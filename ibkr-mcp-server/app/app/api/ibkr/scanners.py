"""Scanner-related tools."""

from fastapi import Query
from app.api.ibkr import ibkr_router, ib_interface
from app.core.setup_logging import logger
from app.models import ScannerRequest
from pydantic import ValidationError


@ibkr_router.get("/scanner/workflow", operation_id="get_scanner_workflow")
async def get_scanner_workflow() -> dict:
  """Get step-by-step workflow for using scanner effectively.

  Returns a guide on how to use the scanner endpoints efficiently,
  including the recommended order of operations and best practices.

  Returns:
    dict: Step-by-step workflow and usage tips

  Example:
    >>> get_scanner_workflow()
    {
      "workflow": [
        {"step": 1, "action": "get_scanner_instrument_codes", "description": "..."},
        ...
      ],
      "tips": ["Always call the code endpoints first", ...]
    }

  """
  logger.debug("Returning scanner workflow")
  return {
    "workflow": [
      {
        "step": 1,
        "action": "get_scanner_instrument_codes",
        "description": "Get available instrument types (STK, FUT, OPT)",
        "endpoint": "/scanner/instrument_codes",
      },
      {
        "step": 2,
        "action": "get_scanner_location_codes",
        "description": "Get available location codes (STK.US, STK.EU, etc.)",
        "endpoint": "/scanner/location_codes",
      },
      {
        "step": 3,
        "action": "get_scanner_scan_codes",
        "description": "Get available scan codes for predefined scans",
        "endpoint": "/scanner/scan_codes",
      },
      {
        "step": 4,
        "action": "get_scanner_filter_codes",
        "description": "Get available filter parameters with examples",
        "endpoint": "/scanner/filter_codes",
      },
      {
        "step": 5,
        "action": "get_scanner_results",
        "description": "Execute scanner query with scan_code and empty filters",
        "endpoint": "/scanner/results",
      },
      {
        "step": 6,
        "action": "get_scanner_results",
        "description": "Fine-tune results by adding filters progressively",
        "endpoint": "/scanner/results",
      },
    ],
    "tips": [
      "Always call the code endpoints first to get valid parameters",
      "Use scan_code for predefined scans (e.g., TOP_PERC_GAIN, MOST_ACTIVE)",
      "Use filters for fine-tuning scan_code results",
      "Common filters: priceAbove, priceBelow, marketCapAbove1e6, avgVolumeAbove",
      "Use comma-separated filters: 'priceAbove=10,marketCapAbove1e6=1000'",
    ],
    "examples": {
      "scan_code": {
        "description": "Use predefined scan code",
        "request": {
          "instrument_code": "STK",
          "location_code": "STK.US",
          "scan_code": "TOP_PERC_GAIN",
          "max_results": 25,
        },
      },
      "scan_code_with_filters": {
        "description": "Use scan_code, fine-tune with filters",
        "request": {
          "instrument_code": "STK",
          "location_code": "STK.US",
          "scan_code": "TOP_PERC_GAIN",
          "filters": "priceAbove=10,marketCapAbove1e6=1000",
          "max_results": 25,
        },
      },
    },
  }


@ibkr_router.get(
  "/scanner/instrument_codes",
  operation_id="get_scanner_instrument_codes",
)
async def get_scanner_instrument_codes() -> dict:
  """Get detailed scanner instrument codes with descriptions.

  Returns available instrument types with descriptions and usage information.

  Returns:
    dict: Instrument codes with descriptions and examples

  Example:
    >>> get_scanner_instrument_codes()
    {
      "instrument_codes": ["STK", "FUT", "OPT", "IND", "CASH"],
      "descriptions": {
        "STK": "Stocks and ETFs",
        "FUT": "Futures contracts",
        "OPT": "Options contracts",
        "IND": "Indices",
        "CASH": "Forex and currencies"
      },
      "usage": "Use instrument_code parameter in scanner queries"
    }

  """
  try:
    logger.debug("Getting scanner instrument codes")
    tags = await ib_interface.get_scanner_instrument_codes()

    # Create detailed response with descriptions
    descriptions = {
      "STK": "Stocks and ETFs",
      "FUT": "Futures contracts",
      "OPT": "Options contracts",
      "IND": "Indices",
      "CASH": "Forex and currencies",
      "BOND": "Bonds",
      "CMDTY": "Commodities",
    }

  except Exception as e:
    logger.error("Error in get_scanner_instrument_codes: {!s}", str(e))
    return {"error": "Error getting scanner instrument codes"}
  else:
    logger.debug("Scanner instrument codes: {tags}", tags=tags)
    return {
      "instrument_codes": tags,
      "count": len(tags),
      "descriptions": descriptions,
      "usage": "Use instrument_code parameter in scanner queries",
    }


@ibkr_router.get("/scanner/location_codes", operation_id="get_scanner_location_codes")
async def get_scanner_location_codes() -> dict:
  """Get detailed scanner location codes with descriptions.

  Returns available location codes with descriptions and regional information.

  Returns:
    dict: Location codes with descriptions and examples

  Example:
    >>> get_scanner_location_codes()
    {
      "location_codes": ["STK.US", "STK.EU", "STK.ASIA"],
      "descriptions": {
        "STK.US": "US stocks and ETFs",
        "STK.EU": "European stocks",
        "STK.ASIA": "Asian stocks"
      },
      "usage": "Use location_code parameter in scanner queries"
    }

  """
  try:
    logger.debug("Getting scanner location codes")
    tags = await ib_interface.get_scanner_location_codes()
    descriptions = {
      "STK.US": "US stocks and ETFs",
      "STK.EU": "European stocks",
    }
  except Exception as e:
    logger.error("Error in get_scanner_location_codes: {!s}", str(e))
    return {"error": "Error getting scanner location codes"}
  else:
    logger.debug("Scanner location codes: {tags}", tags=tags)
    return {
      "location_codes": tags,
      "count": len(tags),
      "descriptions": descriptions,
      "usage": "Use location_code parameter in scanner queries",
    }


@ibkr_router.get("/scanner/scan_codes", operation_id="get_scanner_scan_codes")
async def get_scanner_scan_codes() -> dict:
  """Get detailed scanner scan codes with descriptions.

  Returns available scan codes with descriptions and usage information.

  Returns:
    dict: Scan codes with descriptions and examples

  Example:
    >>> get_scanner_scan_codes()
    {
      "scan_codes": ["TOP_PERC_GAIN", "TOP_PERC_LOSE", "MOST_ACTIVE"],
      "descriptions": {
        "TOP_PERC_GAIN": "Stocks with highest percentage gains",
        "TOP_PERC_LOSE": "Stocks with highest percentage losses",
        "MOST_ACTIVE": "Stocks with highest trading volume"
      },
      "usage": "Use scan_code parameter in scanner queries"
    }

  """
  try:
    logger.debug("Getting scanner scan codes")
    tags = await ib_interface.get_scanner_scan_codes()

    # Create detailed response with descriptions
    descriptions = {
      "TOP_PERC_GAIN": "Stocks with highest percentage gains",
      "TOP_PERC_LOSE": "Stocks with highest percentage losses",
      "MOST_ACTIVE": "Stocks with highest trading volume",
      "HOT_CONTRACTS": "Contracts with unusual activity",
    }

  except Exception as e:
    logger.error("Error in get_scanner_scan_codes: {!s}", str(e))
    return {"error": "Error getting scanner scan codes"}
  else:
    logger.debug("Scanner scan codes: {tags}", tags=tags)
    return {
      "scan_codes": tags,
      "descriptions": descriptions,
      "count": len(tags),
      "usage": "Use scan_code parameter in scanner queries",
      "tips": [
        "Use scan_codes for predefined market scans",
        "Use filter codes to fine tune the results of a scan_code",
        "Common scan_codes: TOP_PERC_GAIN, MOST_ACTIVE, HOT_CONTRACTS",
      ],
    }


@ibkr_router.get("/scanner/filter_codes", operation_id="get_scanner_filter_codes")
async def get_scanner_filter_codes() -> dict:
  """Get detailed scanner filter codes with examples and usage hints.

  Returns available filter codes with examples and descriptions for common filters.

  Returns:
    dict: Filter codes with examples and usage information

  Example:
    >>> get_scanner_filter_codes()
    {
      "filter_codes": ["priceAbove", "priceBelow", "marketCapAbove", ...],
      "examples": [
        {"code": "priceAbove", "example": "priceAbove=10", "type": "float"},
        ...
      ],
      "usage": "Use filters in 'parameter=value' format, e.g., "
      " 'priceAbove=10,marketCapAbove1e6=1000'"
    }

  """
  try:
    logger.debug("Getting scanner filter codes")
    tags = await ib_interface.get_scanner_filter_codes()

  except Exception as e:
    logger.error("Error in get_scanner_filter_codes: {!s}", str(e))
    return {"error": "Error getting scanner filter codes"}
  else:
    logger.debug("Scanner filter codes: {tags}", tags=tags)
    return {
      "filter_codes": tags,
      "count": len(tags),
      "usage": "Use filters to fine-tune scan_code results in 'parameter=value' format,"
      " e.g., 'priceAbove=10,marketCapAbove1e6=1000'",
      "tips": [
        "Combine multiple filters to narrow results",
        "Use marketCapAbove1e6 to filter by cap, use numbers in millions USD",
        "Use priceAbove to filter out penny stocks",
        "Use avgVolumeAbove to ensure liquidity",
      ],
    }


@ibkr_router.get("/scanner/results", operation_id="get_scanner_results")
async def get_scanner_results(
  instrument_code: str = Query(
    description="Instrument type (STK, FUT, OPT). Call get_scanner_instrument_codes() first.",  # noqa: E501
  ),
  location_code: str = Query(
    description="Location code (e.g., STK.US, STK.EU). Call get_scanner_location_codes() first.",  # noqa: E501
  ),
  scan_code: str | None = Query(
    default=None,
    description="""
    Scan code for predefined scans (e.g., 'TOP_PERC_GAIN', 'MOST_ACTIVE').
    Call get_scanner_scan_codes() to see all available scan codes.
    Must submit scan_code, 'MOST_ACTIVE' is a good default.
    """,
  ),
  filters: str | None = Query(
    default=None,
    description="""
    Comma-separated filters in 'parameter=value' format.
    These are used to fine-tune scan_code results.
    Examples: 'priceAbove=10,marketCapAbove1e6=1000' or
    'priceAbove=10,avgVolumeAbove=1000000'
    Common filters: priceAbove, priceBelow, marketCapAbove1e6, avgVolumeAbove
    Call get_scanner_filter_codes() to see all available filters with examples.
    """,
  ),
  max_results: int = Query(
    default=50,
    description="Maximum number of results to return (1-50)",
  ),
) -> str:
  """Get scanner results from Interactive Brokers TWS.

  This function queries the IB TWS scanner with specified parameters to find
  instruments matching the given criteria.

  Args:
    instrument_code (str): Type of instrument to scan for (e.g., 'STK', 'FUT', 'OPT')
    location_code (str): Geographic location/market code (e.g., 'STK.US', 'STK.EU')
    scan_code (str): Predefined scan type (e.g., 'TOP_PERC_GAIN', 'MOST_ACTIVE').
    filters (str, optional): Used to fine-tune scan_code results.
      Comma-separated parameters in 'parameter=value' format,
      e.g. 'priceAbove=10,marketCapAbove1e6=1000'
    max_results (int): Maximum number of results to return

  Returns:
    str: A formatted string containing the scanner results or error message

  Example:
    >>> get_scanner_results(
      instrument_code="STK",
      location_code="STK.US",
      scan_code="TOP_PERC_GAIN",
      filters="priceAbove=10,marketCapAbove1e6=1000",
      max_results=25
    )
    "I found 3 stocks matching the scanner parameters: ['AAPL', 'MSFT', 'GOOGL']"

  """
  try:
    # Use Pydantic model for validation and parsing
    try:
      scanner_request = ScannerRequest.from_string_filters(
        instrument_code=instrument_code,
        location_code=location_code,
        filters_str=filters,
        scan_code=scan_code,
        max_results=max_results,
      )
    except ValidationError as e:
      error_details = "; ".join(
        [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()],
      )
      return f"Error: Invalid scanner parameters - {error_details}"
    except ValueError as e:
      return f"Error: {str(e)!r}"

    logger.debug(
      f"""
      Getting scanner results for instrument code: {scanner_request.instrument_code},
      location code: {scanner_request.location_code},
      filters: {filters},
      scan_code: {scanner_request.scan_code},
      max results: {scanner_request.max_results}
      parsed filter codes: {scanner_request.get_filter_codes()},
      """,
    )
    results = await ib_interface.get_scanner_results(scanner_request)
  except Exception as e:
    logger.error("Error in get_scanner_results: {!s}", str(e))
    return "Error getting scanner results"
  else:
    logger.debug("Scanner results: {results}", results=results)
    return f"I found {len(results)} stocks matching the scanner parameters: {results}"
