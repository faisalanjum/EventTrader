#!/usr/bin/env python3
"""
Earnings Analysis Event Trigger
================================
Listens to Redis queue, triggers full earnings analysis via Claude Agent SDK.

Tested: 2026-01-16
SDK Version: 0.1.19

Usage:
    source venv/bin/activate
    python scripts/earnings_trigger.py

How it works:
    1. Waits for accession numbers on Redis queue "earnings:trigger"
    2. Triggers /earnings-orchestrator skill for each accession
    3. Skill chain runs: orchestrator → prediction → attribution → neo4j-*
    4. Output written to: predictions.csv, Companies/{ticker}/{accession}.md

Test:
    # In another terminal, push a test accession:
    redis-cli -h 192.168.40.72 -p 31379 LPUSH earnings:trigger "0000320193-23-000005"
"""
import asyncio
import logging
import os
from datetime import datetime

# Must run from project root for setting_sources to find .claude/
os.chdir("/home/faisal/EventMarketDB")

import redis.asyncio as redis
from claude_agent_sdk import query, ClaudeAgentOptions

# Configuration
REDIS_HOST = "192.168.40.72"
REDIS_PORT = 31379
QUEUE_NAME = "earnings:trigger"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)


async def process_earnings(accession_no: str):
    """
    Trigger full earnings analysis for an 8-K filing.

    This invokes /earnings-orchestrator which chains:
    - /earnings-prediction (with PIT filtering)
    - /earnings-attribution (with full data access)
    - /neo4j-* skills for data queries
    - /perplexity-* skills for consensus estimates

    Output:
    - predictions.csv (prediction + actual results)
    - Companies/{ticker}/{accession}.md (full attribution report)
    """
    start_time = datetime.now()
    log.info(f"Starting: {accession_no}")

    try:
        async for msg in query(
            prompt=f"/earnings-orchestrator {accession_no}",
            options=ClaudeAgentOptions(
                setting_sources=["project"],       # Loads .claude/ directory
                permission_mode="bypassPermissions", # No prompts
            )
        ):
            # Log progress
            if hasattr(msg, 'data'):
                data = msg.data
                if data.get('type') == 'tool_use':
                    log.debug(f"Tool: {data.get('name', 'unknown')}")

            # Log final output
            if hasattr(msg, 'result'):
                result = str(msg.result)
                # Log first 500 chars of result
                log.info(f"Output: {result[:500]}...")

        elapsed = (datetime.now() - start_time).total_seconds()
        log.info(f"Completed: {accession_no} ({elapsed:.1f}s)")

    except Exception as e:
        log.error(f"Failed: {accession_no} - {e}")
        raise


async def main():
    """
    Main event loop - listens to Redis and processes earnings.
    """
    log.info(f"Connecting to Redis {REDIS_HOST}:{REDIS_PORT}")
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    # Verify connection
    try:
        await r.ping()
        log.info("Redis connected")
    except Exception as e:
        log.error(f"Redis connection failed: {e}")
        return

    log.info(f"Listening on queue: {QUEUE_NAME}")
    log.info("Push accession numbers to trigger analysis:")
    log.info(f"  redis-cli LPUSH {QUEUE_NAME} <accession_no>")

    while True:
        try:
            # Block until item available
            result = await r.blpop(QUEUE_NAME, timeout=0)
            if result:
                _, accession = result
                accession_no = accession.decode().strip()

                if accession_no:
                    await process_earnings(accession_no)

        except redis.ConnectionError as e:
            log.error(f"Redis connection lost: {e}")
            log.info("Reconnecting in 5s...")
            await asyncio.sleep(5)

        except Exception as e:
            log.error(f"Error: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Shutting down")
