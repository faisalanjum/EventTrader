"""Contract and options-related tools."""

from app.api.ibkr import ibkr_router, ib_interface
from app.core.setup_logging import logger
from app.models import TickerData, OptionsRequest


@ibkr_router.get(
  "/tickers",
  operation_id="get_tickers",
  response_model=list[TickerData],
)
async def get_tickers(
  contract_ids: str | None = None,
) -> list[TickerData]:
  """Get tickers for a list of contract IDs.

  This function queries the IB TWS to get the tickers for a list of contract IDs.
  It will return the last price and symbol, and greeks (if applicable).

  Args:
    contract_ids (str): Comma-separated list of contract IDs to get tickers for.

  Returns:
    List[dict]: A list of ticker dictionaries for the contract IDs.
    will include the contractId, symbol, secType, last, bid, ask, and greeks.

  Example:
    await get_tickers("123456,789012")
    [
      {
        "symbol": "AAPL",
        "last": 150.75,
        "greeks": {
          "delta": 0.5,
        },
      },
      {
        "symbol": "MSFT",
        "last": 210.22,
        "greeks": null,
      },
    ]

  """
  if not contract_ids:
    logger.warning("get_tickers called with no contract_ids")
    return []
  try:
    contract_ids_list = [
      int(cid.strip()) for cid in contract_ids.split(",") if cid.strip()
    ]
    logger.debug(
      "Getting tickers for contract IDs: {contract_ids_list}",
      contract_ids_list=contract_ids_list,
    )
    tickers = await ib_interface.get_tickers(contract_ids_list)
  except Exception as e:
    logger.error("Error in get_tickers: {!s}", str(e))
    return []
  else:
    logger.debug("Tickers: {tickers}", tickers=tickers)
    return tickers


@ibkr_router.post(
  "/filtered_options_tickers",
  operation_id="get_filtered_options_tickers",
  response_model=list[TickerData],
)
async def get_and_filter_options_tickers(
  request: OptionsRequest,
) -> list[TickerData]:
  """Get and filter option chain tickers based on market data criteria.

  This endpoint retrieves an option chain and filters it based on both
  contract-level filters (expirations, strikes) and market-data-level
  criteria (greeks like delta).

  Args:
    request (OptionsRequest): A request body containing the underlying
      contract details, filters, and optional market data criteria.
      you must specify at least one filter to reduce the number of options in the chain,
      you must specify expirations, you can specify tradingClass, strikes, and rights.
      - tradingClass: List of trading classes to filter by.
      - expirations: List of expirations to filter by.
      - strikes: List of strikes to filter by.
      - rights: List of rights to filter by.

  Returns:
    list[TickerData]: A list of filtered ticker data for options that
    match all specified conditions.

  Example (using curl):
    curl -X 'POST'
      'http://127.0.0.1:8000/ibkr/filtered_options_chain'
      -H 'Content-Type: application/json'
      -d '{
        "underlying_symbol": "SPX",
        "underlying_sec_type": "IND",
        "underlying_con_id": 416904,
        "filters": {
          "expirations": ["20250505"],
          "tradingClass": ["SPXW"],
          "rights": ["P"]
        },
        "criteria": {
          "min_delta": -0.06,
          "max_delta": -0.04
        }
      }'

  """
  try:
    logger.debug(
      "Received options tickers request: {request}",
      request=request.model_dump_json(indent=2),
    )

    # `exclude_none=True` ensures we don't pass keys with null values.
    filters_dict = request.filters.model_dump(exclude_none=True)
    criteria_dict = (
      request.criteria.model_dump(exclude_none=True) if request.criteria else None
    )

    filtered_options = await ib_interface.get_and_filter_options(
      request.underlying_symbol,
      request.underlying_sec_type,
      request.underlying_con_id,
      filters_dict,
      criteria_dict,
    )
  except Exception as e:
    logger.error("Error in filter_options_tickers: {!s}", str(e))
    return []
  else:
    logger.debug(
      "Filtered options tickers: {filtered_options}",
      filtered_options=filtered_options,
    )
    return filtered_options
