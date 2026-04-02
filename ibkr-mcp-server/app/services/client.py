"""Base IB client connection handling — long-lived, self-healing."""

import asyncio
import datetime as dt

import exchange_calendars as ecals
from ib_async import IB, util

from app.core.config import get_config
from app.core.setup_logging import logger

# Fixed client IDs avoid collisions with OrderClient (clientId=1)
MARKET_DATA_CLIENT_ID = 10


class IBClient:
    """Base IB client with long-lived connection, heartbeat, and auto-reconnect."""

    def __init__(self) -> None:
        self.config = get_config()
        self.ib = IB()
        self._contract_cache: dict[tuple[str, str, str, str], object] = {}
        self._reconnect_lock = asyncio.Lock()
        self._heartbeat_task: asyncio.Task | None = None
        self._connected_event = asyncio.Event()
        self._shutting_down = False

        # Wire up disconnect handler
        self.ib.disconnectedEvent += self._on_disconnected

    def _on_disconnected(self) -> None:
        """Called by ib_async when the gateway connection drops."""
        self._connected_event.clear()
        if self._shutting_down:
            logger.info("IB disconnected (shutdown)")
            return
        logger.warning("IB connection lost — scheduling reconnect")
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._reconnect_with_backoff())
        except RuntimeError:
            logger.error("No running event loop for reconnect scheduling")

    async def _reconnect_with_backoff(self) -> None:
        """Reconnect with exponential backoff. Max 5 attempts, then wait 60s and retry."""
        async with self._reconnect_lock:
            if self.ib.isConnected():
                self._connected_event.set()
                return

            delays = [1, 2, 5, 10, 30]
            for attempt, delay in enumerate(delays, 1):
                try:
                    logger.info(
                        "Reconnect attempt {}/{} (waiting {}s)...",
                        attempt, len(delays), delay,
                    )
                    await asyncio.sleep(delay)

                    # Clear ib_async's cached event loop to avoid
                    # "Event loop is closed" RuntimeError (ib-async 2.0.1)
                    if hasattr(util.getLoop, "cache_clear"):
                        util.getLoop.cache_clear()

                    # Disconnect cleanly first if in bad state
                    if self.ib.isConnected():
                        self.ib.disconnect()

                    await self.ib.connectAsync(
                        host=self.config.ib_gateway_host,
                        port=self.config.ib_gateway_port,
                        clientId=MARKET_DATA_CLIENT_ID,
                        timeout=20,
                        readonly=False,
                    )
                    self.ib.RequestTimeout = 20
                    self._connected_event.set()
                    self._contract_cache.clear()
                    logger.info("Reconnected to IB gateway on attempt {}", attempt)
                    return
                except Exception as e:
                    logger.warning("Reconnect attempt {} failed: {}", attempt, e)

            # All attempts exhausted — wait 60s and try once more
            logger.error("All reconnect attempts failed. Waiting 60s for final try...")
            await asyncio.sleep(60)
            try:
                if hasattr(util.getLoop, "cache_clear"):
                    util.getLoop.cache_clear()
                if self.ib.isConnected():
                    self.ib.disconnect()
                await self.ib.connectAsync(
                    host=self.config.ib_gateway_host,
                    port=self.config.ib_gateway_port,
                    clientId=MARKET_DATA_CLIENT_ID,
                    timeout=20,
                    readonly=False,
                )
                self.ib.RequestTimeout = 20
                self._connected_event.set()
                self._contract_cache.clear()
                logger.info("Reconnected on final attempt")
            except Exception as e:
                logger.error("Final reconnect failed: {}. Will retry on next request.", e)

    async def _connect(self) -> None:
        """Ensure connection is alive. Uses existing connection if healthy."""
        if self.ib.isConnected():
            return

        # _reconnect_with_backoff is idempotent and lock-protected:
        # - if a reconnect is already in progress, the lock serializes us
        # - if it already succeeded, the isConnected() check inside returns immediately
        # - if it failed, we retry (rather than waiting on an event that was never set)
        await self._reconnect_with_backoff()
        if not self.ib.isConnected():
            raise ConnectionError("Failed to connect to IB gateway")

    async def start_heartbeat(self) -> None:
        """Start periodic heartbeat to detect dead connections proactively."""
        if self._heartbeat_task is not None:
            return
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("IB heartbeat started (30s interval)")

    async def _heartbeat_loop(self) -> None:
        """Ping IB gateway every 30s with reqCurrentTime.

        Also retries reconnection if disconnected — ensures self-healing
        even when no external requests are coming in.
        """
        while not self._shutting_down:
            await asyncio.sleep(30)
            if not self.ib.isConnected():
                logger.info("Heartbeat: not connected — attempting reconnect")
                await self._reconnect_with_backoff()
                continue
            try:
                t = await asyncio.wait_for(
                    self.ib.reqCurrentTimeAsync(),
                    timeout=10,
                )
                logger.debug("Heartbeat OK — IB server time: {}", t)
            except Exception as e:
                logger.warning("Heartbeat failed: {} — triggering reconnect", e)
                self.ib.disconnect()

    async def _qualify_contract(
        self,
        symbol: str,
        sec_type: str,
        exchange: str,
        currency: str,
    ) -> object:
        """Return a qualified Contract, using a cache to avoid redundant IB round-trips."""
        from ib_async.contract import Contract

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
                symbol, exchange, self._contract_cache[key].conId,
            )
        return self._contract_cache[key]

    def _is_market_open(self) -> bool:
        """Return True if the NYSE is currently in a trading minute (UTC)."""
        nyse = ecals.get_calendar("NYSE")
        return nyse.is_trading_minute(dt.datetime.now(dt.UTC))

    async def shutdown(self) -> None:
        """Graceful shutdown — stop heartbeat and disconnect."""
        self._shutting_down = True
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        if self.ib.isConnected():
            self.ib.disconnect()

    def __del__(self) -> None:
        """Disconnect from IB."""
        try:
            if self.ib and self.ib.isConnected():
                self.ib.disconnect()
        except Exception:
            pass
