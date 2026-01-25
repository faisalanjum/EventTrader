#!/usr/bin/env python3
"""
SDK Trigger for Earnings Orchestrator
======================================
Triggers /earnings-orchestrator skill via Claude Agent SDK.

Usage:
    source venv/bin/activate
    python scripts/earnings/sdk_trigger.py AAPL 2

Arguments:
    TICKER: Company ticker (required)
    SIGMA: Threshold multiplier (optional, default: 2)
"""
import asyncio
import sys
import os
from datetime import datetime

# Must run from project root
os.chdir("/home/faisal/EventMarketDB")

from claude_agent_sdk import query, ClaudeAgentOptions


async def run_orchestrator(ticker: str, sigma: str = "2"):
    """Run earnings-orchestrator for a ticker."""
    args = f"{ticker} {sigma}"

    start_time = datetime.now()
    print(f"=== START: {start_time.strftime('%Y-%m-%d %H:%M:%S')} ===", flush=True)
    print(f"Running /earnings-orchestrator {args}", flush=True)
    print("-" * 50, flush=True)

    async for msg in query(
        prompt=f"Run /earnings-orchestrator {args}",
        options=ClaudeAgentOptions(
            setting_sources=["project"],
            permission_mode="bypassPermissions",
            max_turns=50,
        )
    ):
        # Print progress
        if hasattr(msg, 'content'):
            for block in getattr(msg, 'content', []):
                if hasattr(block, 'name'):
                    print(f"Tool: {block.name}", flush=True)

        # Print final result
        if hasattr(msg, 'result'):
            print("-" * 50, flush=True)
            print(msg.result, flush=True)

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    print("-" * 50, flush=True)
    print(f"=== END: {end_time.strftime('%Y-%m-%d %H:%M:%S')} ===", flush=True)
    print(f"=== TOTAL TIME: {elapsed:.1f}s ({elapsed/60:.1f}m) ===", flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sdk_trigger.py TICKER [SIGMA]")
        print("Example: python sdk_trigger.py AAPL 2")
        sys.exit(1)

    ticker = sys.argv[1]
    sigma = sys.argv[2] if len(sys.argv) > 2 else "2"

    asyncio.run(run_orchestrator(ticker, sigma))
