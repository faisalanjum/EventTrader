#!/usr/bin/env python3
"""Claude Code Worker — processes earnings guidance extraction from Redis queue.

Listens on Redis queue `earnings:trigger` and runs the /guidance-transcript skill
via Claude Agent SDK for each incoming payload.

Deployment: K8s `processing` namespace as `claude-code-worker`
KEDA: Scales 0→1 based on queue depth

Payload formats (JSON):
  {"ticker": "AAPL", "source_id": "AAPL_2025-07-31T17.00.00-04.00"}
  {"ticker": "AAPL", "source_id": "AAPL_2025-07-31T17.00.00-04.00", "mode": "dry_run"}

Or plain source_id string:
  "AAPL_2025-07-31T17.00.00-04.00"

Manual test:
  redis-cli -h redis.infrastructure -p 6379 LPUSH earnings:trigger \
    '{"ticker":"ADBE","source_id":"ADBE_2025-06-12T17.00.00-04.00","mode":"dry_run"}'
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Project root — must chdir before importing SDK so setting_sources finds .claude/
PROJECT_DIR = "/home/faisal/EventMarketDB"
os.chdir(PROJECT_DIR)
sys.path.insert(0, PROJECT_DIR)

import redis.asyncio as aioredis
from claude_agent_sdk import ClaudeAgentOptions, query

# ---------------------------------------------------------------------------
# Configuration from environment (eventtrader-secrets + claude-auth provide these)
# ---------------------------------------------------------------------------
REDIS_HOST = os.environ.get("REDIS_HOST", "redis.infrastructure.svc.cluster.local")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
QUEUE_NAME = os.environ.get("QUEUE_NAME", "earnings:trigger")
RETRY_QUEUE = f"{QUEUE_NAME}:retry"
DEAD_LETTER_QUEUE = f"{QUEUE_NAME}:dead"
MAX_RETRIES = 3

# SDK limits per query
MAX_TURNS = int(os.environ.get("MAX_TURNS", "80"))
MAX_BUDGET_USD = float(os.environ.get("MAX_BUDGET_USD", "5.0"))
DEFAULT_MODE = os.environ.get("DEFAULT_MODE", "write")

# In-cluster MCP HTTP endpoint (overrides .mcp.json stdio server)
MCP_NEO4J_URL = os.environ.get(
    "MCP_NEO4J_URL",
    "http://mcp-neo4j-cypher-http.mcp-services.svc.cluster.local:8000/mcp",
)

# ---------------------------------------------------------------------------
# Logging — stdout (K8s standard) + file log
# ---------------------------------------------------------------------------
LOG_DIR = Path(PROJECT_DIR) / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "claude-worker.log"),
    ],
)
log = logging.getLogger("claude-worker")

# ---------------------------------------------------------------------------
# Graceful shutdown (SIGTERM from K8s, SIGINT from Ctrl-C)
# ---------------------------------------------------------------------------
shutdown_event = asyncio.Event()


def _handle_signal(signum, _frame):
    log.info("Received signal %s — initiating graceful shutdown", signum)
    shutdown_event.set()


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


# ---------------------------------------------------------------------------
# Payload parsing
# ---------------------------------------------------------------------------
def parse_payload(raw: bytes) -> dict:
    """Parse queue payload — supports JSON object or plain source_id string."""
    text = raw.decode("utf-8").strip()
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except (json.JSONDecodeError, ValueError):
        pass
    # Fallback: plain source_id string — extract ticker from "TICKER_YYYY-..." pattern
    ticker = text.split("_")[0] if "_" in text else "UNKNOWN"
    return {"ticker": ticker, "source_id": text}


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------
async def process_item(payload: dict) -> bool:
    """Run /guidance-transcript for a single queue item. Returns True on success."""
    ticker = payload.get("ticker", "UNKNOWN")
    source_id = payload.get("source_id", "")
    mode = payload.get("mode", DEFAULT_MODE)

    if not source_id:
        log.error("Missing source_id in payload: %s", payload)
        return False

    prompt = f"/guidance-transcript {ticker} transcript {source_id} MODE={mode}"
    log.info("Processing: %s", prompt)

    start = time.monotonic()

    try:
        options = ClaudeAgentOptions(
            setting_sources=["project"],
            cwd=PROJECT_DIR,
            permission_mode="bypassPermissions",
            max_turns=MAX_TURNS,
            max_budget_usd=MAX_BUDGET_USD,
            # Override neo4j-cypher to use in-cluster HTTP (not stdio from .mcp.json)
            # Host header required: MCP server rejects non-localhost Host values
            mcp_servers={
                "neo4j-cypher": {
                    "type": "http",
                    "url": MCP_NEO4J_URL,
                    "headers": {"Host": "localhost:8000"},
                },
            },
        )

        result_text = None
        async for msg in query(prompt=prompt, options=options):
            if hasattr(msg, "result"):
                result_text = msg.result

        elapsed = time.monotonic() - start

        if result_text is None:
            log.error("No result returned for %s (elapsed: %.0fs)", source_id, elapsed)
            return False

        log.info("Completed %s in %.0fs", source_id, elapsed)
        # Log a summary — first 500 chars
        log.info("Result: %s", result_text[:500])
        return True

    except Exception:
        elapsed = time.monotonic() - start
        log.error("Failed %s after %.0fs", source_id, elapsed, exc_info=True)
        return False


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
async def main():
    node = os.environ.get("NODE_NAME", "unknown")
    log.info("=" * 60)
    log.info("Claude Code Worker starting")
    log.info("  Node: %s", node)
    log.info("  Redis: %s:%s", REDIS_HOST, REDIS_PORT)
    log.info("  Queue: %s", QUEUE_NAME)
    log.info("  MCP Neo4j: %s", MCP_NEO4J_URL)
    log.info("  Max turns: %s, Max budget: $%s", MAX_TURNS, MAX_BUDGET_USD)
    log.info("  Default mode: %s", DEFAULT_MODE)
    log.info("=" * 60)

    r = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)

    try:
        await r.ping()
        log.info("Redis connected")
    except Exception as e:
        log.error("Redis connection failed: %s", e)
        sys.exit(1)

    log.info("Listening on %s ...", QUEUE_NAME)

    while not shutdown_event.is_set():
        try:
            # BRPOP with 5s timeout — FIFO order (LPUSH left, BRPOP right)
            # Short timeout lets us check shutdown_event regularly
            result = await r.brpop(QUEUE_NAME, timeout=5)
            if result is None:
                continue  # Timeout — loop back and check shutdown_event

            _, raw_payload = result
            payload = parse_payload(raw_payload)
            log.info("Dequeued: %s", json.dumps(payload))

            success = await process_item(payload)

            if not success:
                retry_count = payload.get("_retry", 0) + 1
                if retry_count <= MAX_RETRIES:
                    payload["_retry"] = retry_count
                    await r.lpush(RETRY_QUEUE, json.dumps(payload))
                    log.warning(
                        "Retry queue (attempt %d/%d): %s",
                        retry_count,
                        MAX_RETRIES,
                        payload.get("source_id"),
                    )
                else:
                    await r.lpush(DEAD_LETTER_QUEUE, json.dumps(payload))
                    log.error(
                        "Dead-lettered after %d attempts: %s",
                        retry_count,
                        payload.get("source_id"),
                    )

        except aioredis.ConnectionError as e:
            log.error("Redis connection lost: %s", e)
            if not shutdown_event.is_set():
                log.info("Reconnecting in 5s...")
                await asyncio.sleep(5)

        except Exception:
            log.error("Unexpected error in main loop", exc_info=True)
            if not shutdown_event.is_set():
                await asyncio.sleep(1)

    log.info("Shutdown complete")
    await r.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Interrupted")
