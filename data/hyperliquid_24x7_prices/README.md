# Hyperliquid 24/7 prices

Free, no-key prices from the `xyz` market on Hyperliquid. It covers a small set
of stocks plus commodities, currencies, indexes, ETFs, and crypto.

Live check on 2026-07-19: 102 markets, 87 with non-zero daily volume. Snapshot,
funding-history, and candle requests all succeeded.

## Run

From the repository root:

```bash
python3 data/hyperliquid_24x7_prices/pull_prices.py --snapshot --live-only
python3 data/hyperliquid_24x7_prices/pull_prices.py --macro
python3 data/hyperliquid_24x7_prices/pull_prices.py --funding GOLD --hours 72
python3 data/hyperliquid_24x7_prices/pull_prices.py --candles SILVER --interval 1h --hours 72
```

Add `--jsonl data/hyperliquid_24x7_prices/snapshots.jsonl` to keep snapshots.
JSONL runtime files in this folder are ignored by Git.

## Test

```bash
python3 -m unittest discover -s data/hyperliquid_24x7_prices -p 'test_*.py' -v
```

## Limits

- Off-hours stock values are market and oracle estimates, not official exchange trades.
- Coverage is small and concentrated in large technology and macro markets.
- Use it as an overnight or weekend signal, not as a Massive replacement.
