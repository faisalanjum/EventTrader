"""Pydantic models for options and contract requests."""

from pydantic import BaseModel, Field, ConfigDict


class OptionsFilters(BaseModel):
  """Filters to apply to the options chain."""

  model_config = ConfigDict(populate_by_name=True)

  expirations: list[str] = Field(
    ...,
    description="List of expiration dates in YYYYMMDD format (required)",
  )
  trading_class: list[str] | None = Field(
    default=None,
    alias="tradingClass",
    description="List of trading classes to filter by",
  )
  strikes: list[float] | None = Field(
    default=None,
    description="List of strike prices to filter by",
  )
  rights: list[str] | None = Field(
    default=None,
    description="List of rights to filter by (C for calls, P for puts)",
  )


class OptionsCriteria(BaseModel):
  """Market data criteria to filter options by."""

  min_delta: float | None = Field(default=None, description="Minimum delta value")
  max_delta: float | None = Field(default=None, description="Maximum delta value")
  min_gamma: float | None = Field(default=None, description="Minimum gamma value")
  max_gamma: float | None = Field(default=None, description="Maximum gamma value")
  min_theta: float | None = Field(default=None, description="Minimum theta value")
  max_theta: float | None = Field(default=None, description="Maximum theta value")
  min_vega: float | None = Field(default=None, description="Minimum vega value")
  max_vega: float | None = Field(default=None, description="Maximum vega value")


class OptionsRequest(BaseModel):
  """Request model for filtered options chain endpoint."""

  underlying_symbol: str = Field(
    ...,
    description="Symbol of the underlying contract",
  )
  underlying_sec_type: str = Field(
    ...,
    description="Security type of the underlying contract",
  )
  underlying_con_id: int = Field(
    ...,
    description="Contract ID of the underlying contract",
  )
  filters: OptionsFilters = Field(
    ...,
    description="Filters to apply to the options chain",
  )
  criteria: OptionsCriteria | None = Field(
    default=None,
    description="Optional market data criteria to filter by",
  )


class ContractOptions(BaseModel):
  """Optional parameters for contract details."""

  model_config = ConfigDict(populate_by_name=True)

  last_trade_date_or_contract_month: str | None = Field(
    default=None,
    alias="lastTradeDateOrContractMonth",
    description="Expiry date for options in YYYYMMDD format",
  )
  strike: float | None = Field(
    default=None,
    description="Strike price for options",
  )
  right: str | None = Field(
    default=None,
    description="Right for options - 'C' for calls or 'P' for puts",
  )
  trading_class: str | None = Field(
    default=None,
    alias="tradingClass",
    description="Trading class (e.g., 'SPXW' for weekly SPX options)",
  )


class ContractDetailsRequest(BaseModel):
  """Request model for contract details endpoint."""

  symbol: str = Field(
    ...,
    description="Symbol to get contract details for",
  )
  sec_type: str = Field(
    ...,
    description="Security type (STK, IND, CASH, BAG, BOND, FUT, OPT)",
  )
  exchange: str = Field(
    ...,
    description="Exchange (CBOE, NYSE, ARCA, BATS, NASDAQ)",
  )
  options: ContractOptions | None = Field(
    default=None,
    description="Optional parameters for options contracts",
  )


class OptionsChainRequest(BaseModel):
  """Request model for options chain endpoint."""

  underlying_symbol: str = Field(..., description="Symbol of the underlying contract")
  underlying_sec_type: str = Field(..., description="Security type of the underlying")
  underlying_con_id: int = Field(..., description="Contract ID of the underlying")
  filters: OptionsFilters = Field(
    ...,
    description="Filters to apply to the options chain",
  )
