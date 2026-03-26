"""Position operations."""

import pandas as pd
from ib_async import util

from .client import IBClient
from app.core.setup_logging import logger


class PositionClient(IBClient):
  """Position operations.

  Available public methods:
    - get_positions: get account positions

  """

  async def get_positions(self) -> list[dict]:
    """Get account positions."""
    try:
      await self._connect()
      positions = util.df(self.ib.positions())
      if positions is None or positions.empty:
        return []

      # Safely handle multiplier conversion with error checking
      def safe_cost_calculation(row: pd.Series) -> float:
        try:
          multiplier = float(row["contract"].multiplier or 1)
          return row["avgCost"] / multiplier
        except (ValueError, TypeError, AttributeError):
          logger.warning(f"Invalid multiplier {row['contract'].localSymbol}, using 1")
          return row["avgCost"]

      positions["contractId"] = positions["contract"].apply(lambda x: x.conId)
      positions["avgCost"] = positions.apply(safe_cost_calculation, axis=1)
      positions["contract"] = positions["contract"].apply(lambda x: x.localSymbol)

      # Remove sensitive information
      del positions["account"]
    except Exception as e:
      logger.error("Error getting positions: {}", str(e))
      raise
    else:
      return positions.to_dict(orient="records")
