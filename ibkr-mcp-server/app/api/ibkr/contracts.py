"""Contract and options-related tools."""

from loguru import logger
from app.api.ibkr import ibkr_router, ib_interface
from app.models import ContractDetailsRequest, OptionsChainRequest


@ibkr_router.post("/contract_details", operation_id="get_contract_details")
async def get_contract_details(
  request: ContractDetailsRequest,
) -> str:
  """Get contract details for a given symbol.

  Args:
    request (ContractDetailsRequest): Request containing symbol, security type,
      exchange, and optional parameters for options contracts.

  Returns:
    str: A formatted string containing the contract details or error message

  Example (using curl):
    curl -X 'POST'
      'http://127.0.0.1:8000/ibkr/contract_details'
      -H 'Content-Type: application/json'
      -d '{
        "symbol": "AAPL",
        "sec_type": "STK",
        "exchange": "NASDAQ"
      }'

  """
  try:
    logger.debug("Getting contract details for symbol: {symbol}", symbol=request.symbol)
    options_dict = (
      request.options.model_dump(exclude_none=True) if request.options else {}
    )
    details = await ib_interface.get_contract_details(
      symbol=request.symbol,
      sec_type=request.sec_type,
      exchange=request.exchange,
      options=options_dict,
    )
  except Exception as e:
    logger.error("Error in get_contract_details: {!s}", str(e))
    return "Error getting contract details"
  else:
    logger.debug("Contract details: {details}", details=details)
    return f"The contract details for the symbol are: {details}"


@ibkr_router.post("/options_chain", operation_id="get_options_chain")
async def get_options_chain(request: OptionsChainRequest) -> str:
  """Get options chain for a given underlying contract.

  Args:
    request (OptionsChainRequest): Request containing underlying contract details
      and filters to apply to the options chain.

  Returns:
    str: A formatted string containing the options chain or error message

  Example (using curl):
    curl -X 'POST'
      'http://127.0.0.1:8000/ibkr/options_chain'
      -H 'Content-Type: application/json'
      -d '{
        "underlying_symbol": "SPX",
        "underlying_sec_type": "IND",
        "underlying_con_id": 416904,
        "filters": {
          "expirations": ["20250505"],
          "tradingClass": ["SPXW"],
          "rights": ["C", "P"],
          "strikes": [5490]
        }
      }'

  """
  try:
    logger.debug(
      "Getting options chain for symbol: {symbol}",
      symbol=request.underlying_symbol,
    )
    filters_dict = request.filters.model_dump(exclude_none=True)
    options_chain = await ib_interface.get_options_chain(
      request.underlying_symbol,
      request.underlying_sec_type,
      request.underlying_con_id,
      filters_dict,
    )
  except Exception as e:
    logger.error("Error in get_options_chain: {!s}", str(e))
    return "Error getting options chain"
  else:
    logger.debug("Options chain: {options_chain}", options_chain=options_chain)
    return f"The available options contracts are: {options_chain}"
