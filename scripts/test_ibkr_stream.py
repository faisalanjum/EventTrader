#!/usr/bin/env python3
"""
Isolated IBKR streaming price test.

Connects to paper gateway, subscribes to market data via reqMktData(),
prints each tick to stdout. Designed for use with Claude Code Monitor tool.

Uses clientId=30 to avoid collisions:
  - MCP server: clientId=10
  - Trade daemon: clientId=20/21

Usage:
  python3 scripts/test_ibkr_stream.py AAPL
  python3 scripts/test_ibkr_stream.py AAPL MSFT BTC-USD
"""

import asyncio
import signal
import sys
from datetime import datetime

# ib_async must be in venv
from ib_async import IB, Stock, Crypto, Forex

CLIENT_ID = 30
GATEWAY_HOST = "10.111.180.120"  # paper gateway ClusterIP
GATEWAY_PORT = 4004


def make_contract(symbol: str):
    """Create contract from symbol string."""
    if symbol.endswith("-USD"):
        # Crypto: BTC-USD, ETH-USD
        base = symbol.split("-")[0]
        return Crypto(base, "PAXOS", "USD")
    elif "/" in symbol:
        # Forex: EUR/USD
        pair = symbol.replace("/", "")
        return Forex(pair)
    else:
        # Stock
        return Stock(symbol, "SMART", "USD")


def on_price_update(ticker, symbol: str, last_prices: dict):
    """Callback for each market data tick."""
    last = ticker.last if ticker.last == ticker.last else None  # NaN check
    bid = ticker.bid if ticker.bid == ticker.bid else None
    ask = ticker.ask if ticker.ask == ticker.ask else None

    # Only print when price actually changed
    prev = last_prices.get(symbol)
    current = last or bid or ask
    if current is None:
        return
    if prev is not None and abs(current - prev) < 0.001:
        return

    last_prices[symbol] = current
    ts = datetime.now().strftime("%H:%M:%S")

    parts = [f"{symbol}"]
    if last is not None:
        parts.append(f"last={last:.2f}")
    if bid is not None and ask is not None:
        parts.append(f"bid={bid:.2f}")
        parts.append(f"ask={ask:.2f}")

    if prev is not None and current != prev:
        diff = current - prev
        arrow = "▲" if diff > 0 else "▼"
        parts.append(f"{arrow}{abs(diff):.2f}")

    print(f"{' | '.join(parts)} | {ts}", flush=True)


async def main(symbols: list[str]):
    ib = IB()
    last_prices: dict[str, float] = {}

    # Graceful shutdown
    shutdown = asyncio.Event()

    def handle_signal(*_):
        shutdown.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_signal)

    try:
        await ib.connectAsync(GATEWAY_HOST, GATEWAY_PORT, clientId=CLIENT_ID, timeout=10)
        print(f"Connected to IBKR paper gateway | clientId={CLIENT_ID} | {datetime.now().strftime('%H:%M:%S')}", flush=True)
    except Exception as e:
        print(f"CONNECTION FAILED: {e}", flush=True)
        return

    # Subscribe to each symbol
    for sym in symbols:
        contract = make_contract(sym)
        try:
            qualified = await ib.qualifyContractsAsync(contract)
            if not qualified:
                print(f"{sym}: contract qualification failed", flush=True)
                continue
            contract = qualified[0]

            # reqMktData with snapshot=False = persistent streaming
            ticker = ib.reqMktData(contract, snapshot=False)
            ticker.updateEvent += lambda t, s=sym: on_price_update(t, s, last_prices)
            print(f"{sym}: subscribed (conId={contract.conId})", flush=True)
        except Exception as e:
            print(f"{sym}: subscription failed — {e}", flush=True)

    # Run until signal
    while not shutdown.is_set():
        await asyncio.sleep(0.1)
        ib.sleep(0)  # process IB events

    # Cleanup
    for sym in symbols:
        try:
            contract = make_contract(sym)
            ib.cancelMktData(contract)
        except Exception:
            pass

    ib.disconnect()
    print(f"Disconnected | {datetime.now().strftime('%H:%M:%S')}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_ibkr_stream.py SYMBOL [SYMBOL ...]", flush=True)
        sys.exit(1)

    symbols = [s.upper() for s in sys.argv[1:]]
    asyncio.run(main(symbols))
