#!/usr/bin/env python3
"""Smoke test for trade daemon IBKR client.

Tests connection, contract qualification, quote fetching, and account/position
queries ONLY. Does NOT place any orders.

Usage:
  python scripts/trade/test_ibkr_smoke.py --account-mode paper
  python scripts/trade/test_ibkr_smoke.py --account-mode paper --symbols AAPL MSFT
  python scripts/trade/test_ibkr_smoke.py --account-mode paper --host localhost --port 4004
"""

import argparse
import asyncio
import logging
import sys

# Add project root to path (derive dynamically, not hardcoded)
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from scripts.trade.ibkr_client import IBKRConfig, TradeDaemonIBClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("smoke_test")


async def run_smoke_test(config: IBKRConfig, symbols: list[str]) -> bool:
    """Run smoke test. Returns True if all tests pass."""
    client = TradeDaemonIBClient(config)
    passed = 0
    failed = 0

    try:
        # Test 1: Connect
        logger.info("=" * 60)
        logger.info("TEST 1: Connect to IBKR Gateway (%s:%d)", config.host, config.port)
        logger.info("=" * 60)
        await client.connect()
        assert client.is_connected, "Not connected after connect()"
        logger.info("✓ Connected (mktdata=%d, orders=%d)", config.mktdata_client_id, config.order_client_id)
        passed += 1

        # Test 2: Qualify contracts
        logger.info("")
        logger.info("=" * 60)
        logger.info("TEST 2: Qualify contracts")
        logger.info("=" * 60)
        contracts = {}
        for sym in symbols:
            contract = await client.qualify_stock(sym)
            contracts[sym] = contract
            min_tick = client.get_min_tick(contract)
            logger.info("✓ %s → conId=%d, exchange=%s, minTick=%s",
                        sym, contract.conId, contract.exchange, min_tick)
        passed += 1

        # Test 3: Get quotes
        logger.info("")
        logger.info("=" * 60)
        logger.info("TEST 3: Get quotes")
        logger.info("=" * 60)
        for sym in symbols:
            quote = await client.get_quote(sym)
            logger.info(
                "✓ %s → bid=%.2f, ask=%.2f, last=%.2f, spread=%.4f%%, close=%s",
                sym,
                quote.bid or 0,
                quote.ask or 0,
                quote.last or 0,
                quote.spread_pct or 0,
                f"{quote.close:.2f}" if quote.close else "N/A",
            )
        passed += 1

        # Test 4: Account summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("TEST 4: Account summary")
        logger.info("=" * 60)
        summary = await client.get_account_summary()
        logger.info("✓ Net liquidation: $%.2f", summary.net_liquidation)
        logger.info("  Available funds: $%.2f", summary.available_funds)
        logger.info("  Buying power:    $%.2f", summary.buying_power)
        logger.info("  Unrealized P&L:  $%.2f", summary.unrealized_pnl)
        passed += 1

        # Test 5: Positions
        logger.info("")
        logger.info("=" * 60)
        logger.info("TEST 5: Positions")
        logger.info("=" * 60)
        positions = await client.get_positions()
        if positions:
            for p in positions:
                logger.info("✓ %s: qty=%.0f, avg_cost=$%.2f", p.symbol, p.quantity, p.avg_cost)
        else:
            logger.info("✓ No positions (empty portfolio)")
        passed += 1

        # Test 6: Open orders
        logger.info("")
        logger.info("=" * 60)
        logger.info("TEST 6: Open orders")
        logger.info("=" * 60)
        orders = await client.get_open_orders()
        if orders:
            for o in orders:
                logger.info("✓ %s %s %s qty=%.0f status=%s",
                            o.symbol, o.action, o.order_type, o.quantity, o.status)
        else:
            logger.info("✓ No open orders")
        passed += 1

        # Test 7: Tick-size calculation
        logger.info("")
        logger.info("=" * 60)
        logger.info("TEST 7: Tick size and price rounding")
        logger.info("=" * 60)
        from scripts.trade.ibkr_client import round_to_tick, _tick_size_for_price
        for sym in symbols:
            contract = contracts[sym]
            min_tick = client.get_min_tick(contract)
            quote = await client.get_quote(sym)
            if quote.ask:
                tick = _tick_size_for_price(quote.ask, min_tick)
                buffer = max(tick, quote.ask * (config.limit_buffer_pct / 100))
                buy_limit = round_to_tick(quote.ask + buffer, tick)
                logger.info(
                    "✓ %s: ask=$%.4f, tick=$%.4f, buffer=$%.4f → buy_limit=$%.4f",
                    sym, quote.ask, tick, buffer, buy_limit,
                )
            if quote.bid:
                tick = _tick_size_for_price(quote.bid, min_tick)
                buffer = max(tick, quote.bid * (config.limit_buffer_pct / 100))
                sell_limit = round_to_tick(quote.bid - buffer, tick)
                logger.info(
                    "  %s: bid=$%.4f, tick=$%.4f, buffer=$%.4f → sell_limit=$%.4f",
                    sym, quote.bid, tick, buffer, sell_limit,
                )
        passed += 1

        # Test 8: Streaming subscription (subscribe, wait for updates, unsubscribe)
        logger.info("")
        logger.info("=" * 60)
        logger.info("TEST 8: Streaming market data subscription")
        logger.info("=" * 60)
        updates_received: dict[str, int] = {}

        def on_update(symbol: str, ticker):
            updates_received[symbol] = updates_received.get(symbol, 0) + 1

        tickers = await client.subscribe_quotes(symbols, on_update=on_update)
        logger.info("  Subscribed to %d symbols. Waiting 8 seconds for updates...", len(tickers))

        # Wait and let updates flow
        await asyncio.sleep(8)

        for sym in symbols:
            count = updates_received.get(sym, 0)
            t = tickers.get(sym)
            bid = getattr(t, 'bid', None) if t else None
            ask = getattr(t, 'ask', None) if t else None
            last = getattr(t, 'last', None) if t else None
            logger.info(
                "  %s: %d updates, bid=%s, ask=%s, last=%s",
                sym, count,
                f"${bid:.2f}" if bid and bid > 0 else "N/A",
                f"${ask:.2f}" if ask and ask > 0 else "N/A",
                f"${last:.2f}" if last and last > 0 else "N/A",
            )

        logger.info("  Active streaming symbols: %s", client.streaming_symbols)
        await client.unsubscribe_quotes()
        logger.info("  After unsubscribe: %s", client.streaming_symbols)

        total_updates = sum(updates_received.values())
        if total_updates > 0:
            logger.info("✓ Streaming smoke check passed: %d total updates received", total_updates)
        else:
            logger.info("⚠ Streaming smoke check: 0 updates (expected if delayed/frozen data or outside hours)")
            logger.info("  Subscribe/unsubscribe lifecycle worked. Updates will flow with live data subscription.")
        # Always pass — this is a connectivity/lifecycle smoke check, not a data-delivery guarantee.
        # True streaming validation requires DATA_MODE=realtime + IBKR market data subscription.
        passed += 1

    except Exception as e:
        logger.error("✗ FAILED: %s", e, exc_info=True)
        failed += 1

    finally:
        await client.shutdown()

    logger.info("")
    logger.info("=" * 60)
    logger.info("RESULTS: %d passed, %d failed", passed, failed)
    logger.info("=" * 60)
    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Smoke test trade daemon IBKR client")
    parser.add_argument("--account-mode", default="paper", choices=["paper", "live"])
    parser.add_argument("--data-mode", default="delayed", choices=["delayed", "realtime"])
    parser.add_argument("--symbols", nargs="+", default=["AAPL", "MSFT", "SPY"])
    parser.add_argument("--host", help="Override IBKR Gateway host")
    parser.add_argument("--port", type=int, help="Override IBKR Gateway port")
    args = parser.parse_args()

    overrides = {}
    if args.host:
        overrides["host"] = args.host
    if args.port:
        overrides["port"] = args.port

    config = IBKRConfig.from_account_mode(args.account_mode, data_mode=args.data_mode, **overrides)
    logger.info("Config: %s:%d (account=%s, data=%s, mktdata_id=%d, order_id=%d)",
                config.host, config.port, args.account_mode, args.data_mode,
                config.mktdata_client_id, config.order_client_id)

    success = asyncio.run(run_smoke_test(config, args.symbols))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
