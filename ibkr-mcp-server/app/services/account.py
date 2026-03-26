"""Account summary operations."""

from .client import IBClient
from app.core.setup_logging import logger

KEY_TAGS = {
    "NetLiquidation",
    "TotalCashValue",
    "GrossPositionValue",
    "BuyingPower",
    "AvailableFunds",
    "UnrealizedPnL",
    "RealizedPnL",
    "SettledCash",
    "InitMarginReq",
    "MaintMarginReq",
}


class AccountClient(IBClient):
    """Account summary operations."""

    async def get_account_summary(self) -> list[dict]:
        """Get account summary with key financial metrics."""
        try:
            await self._connect()
            values = self.ib.accountValues()
            if not values:
                return []

            result = []
            for av in values:
                if av.tag in KEY_TAGS:
                    try:
                        val = float(av.value)
                    except (ValueError, TypeError):
                        val = av.value
                    result.append({
                        "tag": av.tag,
                        "value": val,
                        "currency": av.currency,
                    })
            return result
        except Exception as e:
            logger.error("Error getting account summary: {}", str(e))
            raise
