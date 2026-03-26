"""Main IB interface combining all functionality."""

from .market_data import MarketDataClient
from .contracts import ContractClient
from .scanners import ScannerClient
from .positions import PositionClient
from .history import HistoryClient
from .account import AccountClient
from .orders import OrderClient


class IBInterface(
  MarketDataClient,
  ContractClient,
  ScannerClient,
  PositionClient,
  HistoryClient,
  AccountClient,
):
  """Main IB interface for market data (shared IB connection, random clientId).

  Order operations use a SEPARATE OrderClient with its own IB() instance
  and fixed clientId=1 to ensure reliable order tracking.
  """

  def __init__(self) -> None:
    super().__init__()
    self.orders = OrderClient()

  # Delegate order methods to the dedicated OrderClient
  async def place_market_order(self, *args, **kwargs):
    return await self.orders.place_market_order(*args, **kwargs)

  async def place_limit_order(self, *args, **kwargs):
    return await self.orders.place_limit_order(*args, **kwargs)

  async def place_stop_order(self, *args, **kwargs):
    return await self.orders.place_stop_order(*args, **kwargs)

  async def place_bracket_order(self, *args, **kwargs):
    return await self.orders.place_bracket_order(*args, **kwargs)

  async def place_trailing_stop_order(self, *args, **kwargs):
    return await self.orders.place_trailing_stop_order(*args, **kwargs)

  async def place_bracket_with_trailing_stop(self, *args, **kwargs):
    return await self.orders.place_bracket_with_trailing_stop(*args, **kwargs)

  async def modify_order(self, *args, **kwargs):
    return await self.orders.modify_order(*args, **kwargs)

  async def cancel_order(self, *args, **kwargs):
    return await self.orders.cancel_order(*args, **kwargs)

  async def get_open_orders(self, *args, **kwargs):
    return await self.orders.get_open_orders(*args, **kwargs)

  async def advanced_order(self, *args, **kwargs):
    return await self.orders.advanced_order(*args, **kwargs)
