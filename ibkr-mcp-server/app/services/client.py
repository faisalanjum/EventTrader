"""Base IB client connection handling."""

import asyncio
import datetime as dt
import secrets

import exchange_calendars as ecals
from ib_async import IB

from app.core.config import get_config
from app.core.setup_logging import logger


class IBClient:
  """Base IB client connection handling. No public methods."""

  def __init__(self) -> None:
    """Initialize IB interface."""
    self.config = get_config()
    self.ib = IB()
    # Qualified contracts keyed by (symbol, sec_type, exchange, currency).
    # qualifyContractsAsync is an IB round-trip; caching eliminates it on repeat calls.
    self._contract_cache: dict[tuple[str, str, str, str], object] = {}

  async def _connect(self) -> None:
    """Create and connect IB client."""
    if self.ib.isConnected():
      return

    host = self.config.ib_gateway_host
    port = self.config.ib_gateway_port

    try:
      await self.ib.connectAsync(
        host=host,
        port=port,
        clientId=secrets.randbelow(32767) + 1,
        timeout=20,
        readonly=False,
      )
      self.ib.RequestTimeout = 20
    except Exception as e:
      logger.error("Error connecting to IB: {}", e)
      raise

  async def _qualify_contract(
    self,
    symbol: str,
    sec_type: str,
    exchange: str,
    currency: str,
  ) -> object:
    """Return a qualified Contract, using a cache to avoid redundant IB round-trips."""
    from ib_async.contract import Contract  # noqa: PLC0415

    key = (symbol.upper(), sec_type.upper(), exchange.upper(), currency.upper())
    if key not in self._contract_cache:
      contract = Contract(
        symbol=symbol,
        secType=sec_type,
        exchange=exchange,
        currency=currency,
      )
      [qualified] = await self.ib.qualifyContractsAsync(contract)
      self._contract_cache[key] = qualified
      logger.debug(
        "Qualified contract {}/{} conId={}",
        symbol,
        exchange,
        self._contract_cache[key].conId,
      )
    return self._contract_cache[key]

  def _is_market_open(self) -> bool:
    """Return True if the NYSE is currently in a trading minute (UTC).

    Used to select live (type 1) vs. frozen (type 2) market data.
    """
    nyse = ecals.get_calendar("NYSE")
    return nyse.is_trading_minute(dt.datetime.now(dt.UTC))

  async def send_command_to_ibc(self, command: str) -> None:
    """Send a command to the IBC Command Server.

    Args:
        command: The command to send to the IBC Command Server

    """
    if not command:
      logger.error("Error: you must supply a valid IBC command")
      return

    host = self.config.ib_gateway_host
    port = self.config.ib_command_server_port

    try:
      # Create connection
      reader, writer = await asyncio.open_connection(host, port)

      # Send command
      writer.write(command.encode() + b"\n")
      await writer.drain()

      # Close connection
      writer.close()
      await writer.wait_closed()

      logger.debug("Successfully sent command to IBC: {}", command)
    except Exception as e:
      logger.error("Error sending command to IBC: {}", str(e))
      raise

  def __del__(self) -> None:
    """Disconnect from IB."""
    try:
      if self.ib and self.ib.isConnected():
        self.ib.disconnect()
    except Exception:
      logger.warning("Error disconnecting from IB")
