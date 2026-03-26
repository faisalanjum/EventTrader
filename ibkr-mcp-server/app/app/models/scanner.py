"""Pydantic models for scanner operations."""

from pydantic import BaseModel, Field, field_validator


class ScannerFilter(BaseModel):
  """Model for a single scanner filter."""

  parameter: str = Field(..., description="Filter parameter name")
  value: str = Field(..., description="Filter value")

  def to_filter_code(self) -> str:
    """Convert to 'parameter=value' format."""
    return f"{self.parameter}={self.value}"


class ScannerRequest(BaseModel):
  """Model for scanner request parameters."""

  instrument_code: str = Field(..., description="Instrument type (STK, FUT, OPT)")
  location_code: str = Field(..., description="Location code (e.g., STK.US, STK.EU)")
  filters: list[ScannerFilter] = Field(default_factory=list)
  scan_code: str | None = Field(default=None)
  max_results: int = Field(default=50, ge=1, le=100)

  @field_validator("instrument_code")
  @classmethod
  def validate_instrument_code(cls, v: str) -> str:
    """Validate instrument code format."""
    valid_codes = ["STK", "FUT", "OPT", "IND", "CASH", "BOND", "CMDTY"]
    if v.upper() not in valid_codes:
      error_msg = f"Invalid instrument code '{v}'. Valid codes: {valid_codes}"
      raise ValueError(error_msg)
    return v.upper()

  @field_validator("location_code")
  @classmethod
  def validate_location_code(cls, v: str) -> str:
    """Validate location code format."""
    if not v or "." not in v:
      error_msg = f"Invalid location code '{v}'. Expected format: 'TYPE.LOCATION'"
      raise ValueError(error_msg)
    return v.upper()

  def get_filter_codes(self) -> list[str]:
    """Get list of filter codes in 'parameter=value' format."""
    return [filter_item.to_filter_code() for filter_item in self.filters]

  @classmethod
  def from_string_filters(
    cls,
    instrument_code: str,
    location_code: str,
    scan_code: str | None,
    filters_str: str | None = None,
    max_results: int = 50,
  ) -> "ScannerRequest":
    """Create ScannerRequest from comma-separated filters string."""
    filters = []

    if filters_str:
      # Split by comma and strip whitespace
      filter_list = [f.strip() for f in filters_str.split(",") if f.strip()]

      for filter_item in filter_list:
        if "=" not in filter_item:
          error_msg = f"Invalid filter format '{filter_item}'. Use 'parameter=value'."
          raise ValueError(error_msg)

        parts = filter_item.split("=", 1)  # Split only on first =
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
          error_msg = f"Invalid filter format '{filter_item}'. Use 'parameter=value'."
          raise ValueError(error_msg)

        filters.append(
          ScannerFilter(parameter=parts[0].strip(), value=parts[1].strip()),
        )

    return cls(
      instrument_code=instrument_code,
      location_code=location_code,
      scan_code=scan_code,
      filters=filters,
      max_results=max_results,
    )
