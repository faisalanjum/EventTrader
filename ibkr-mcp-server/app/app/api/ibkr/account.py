"""Account summary tools."""

from fastapi import HTTPException
from app.api.ibkr import ibkr_router, ib_interface
from app.core.setup_logging import logger


@ibkr_router.get("/account_summary", operation_id="get_account_summary")
async def get_account_summary() -> list[dict]:
    """Get account summary with key financial metrics.

    Returns balances, buying power, margin, and P&L for the connected account.

    Returns:
      list[dict]: Account metrics with tag, value, and currency.

    Example:
      >>> get_account_summary()
      [{"tag":"NetLiquidation","value":100000.0,"currency":"USD"}]

    """
    try:
        logger.debug("Getting account summary")
        summary = await ib_interface.get_account_summary()
    except Exception as e:
        logger.error("Error in get_account_summary: {!s}", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve account summary") from e
    else:
        return summary
