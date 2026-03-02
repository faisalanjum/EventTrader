#!/usr/bin/env python3
"""Claude Code Worker — processes earnings guidance extraction from Redis queue.

Listens on Redis queue `earnings:trigger` and runs the /guidance-transcript skill
via Claude Agent SDK for each incoming payload.

Deployment: K8s `processing` namespace as `claude-code-worker`
KEDA: Scales 0→N based on queue depth (max 7)

Payload formats (JSON):
  Single transcript:
    {"ticker": "AAPL", "source_id": "AAPL_2025-07-31T17.00.00-04.00"}

  Batch (all transcripts for one company, processed sequentially):
    {"ticker": "AAPL", "source_ids": ["AAPL_2025-07-31T...", "AAPL_2025-04-30T..."], "mode": "write"}

  Legacy plain string:
    "AAPL_2025-07-31T17.00.00-04.00"

Status tracking:
  For mode=write, sets guidance_status property on the Transcript node directly.
  Skipped for mode=dry_run.

Trigger:
  python3 scripts/trigger-guidance.py CRM        # queries Neo4j, pushes to Redis
"""

import asyncio
import json
import logging
import os
import platform
import signal
import sys
import time
from pathlib import Path

# Project root — must chdir before importing SDK so setting_sources finds .claude/
PROJECT_DIR = "/home/faisal/EventMarketDB"
os.chdir(PROJECT_DIR)
sys.path.insert(0, PROJECT_DIR)

import redis.asyncio as aioredis
from claude_agent_sdk import ClaudeAgentOptions, query

from neograph.Neo4jConnection import get_manager

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REDIS_HOST = os.environ.get("REDIS_HOST", "redis.infrastructure.svc.cluster.local")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
QUEUE_NAME = os.environ.get("QUEUE_NAME", "earnings:trigger")
DEAD_LETTER_QUEUE = f"{QUEUE_NAME}:dead"
MAX_RETRIES = 3

MAX_TURNS = int(os.environ.get("MAX_TURNS", "80"))
MAX_BUDGET_USD = float(os.environ.get("MAX_BUDGET_USD", "5.0"))
DEFAULT_MODE = "write"

MCP_NEO4J_URL = os.environ.get(
    "MCP_NEO4J_URL",
    "http://mcp-neo4j-cypher-http.mcp-services.svc.cluster.local:8000/mcp",
)

WORKER_POD = platform.node()

# ---------------------------------------------------------------------------
# Logging
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
# Suppress noisy Neo4j driver warnings
logging.getLogger("neo4j").setLevel(logging.ERROR)
log = logging.getLogger("claude-worker")

# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------
shutdown_event = asyncio.Event()


def _handle_signal(signum, _frame):
    log.info("Received signal %s — initiating graceful shutdown", signum)
    shutdown_event.set()


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


# ---------------------------------------------------------------------------
# Status tracking — single property on Transcript node
# ---------------------------------------------------------------------------
def mark_status(mgr, source_id: str, status: str):
    """Set guidance_status on the Transcript node."""
    rows = mgr.execute_cypher_query_all(
        "MATCH (t:Transcript {id: $sid}) SET t.guidance_status = $status RETURN count(t) AS affected",
        {"sid": source_id, "status": status},
    )
    affected = rows[0]["affected"] if rows else 0
    if affected != 1:
        raise RuntimeError(f"mark_status({status}) affected {affected} rows for {source_id}")


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
    ticker = text.split("_")[0] if "_" in text else "UNKNOWN"
    return {"ticker": ticker, "source_id": text}


# ---------------------------------------------------------------------------
# Core processing — single transcript
# ---------------------------------------------------------------------------
async def process_one(ticker: str, source_id: str, mode: str, mgr) -> bool:
    """Run /guidance-transcript for a single transcript. Returns True on success."""
    is_write = mode == "write"

    if is_write and mgr:
        try:
            mark_status(mgr, source_id, "in_progress")
        except Exception as e:
            log.warning("mark_status(in_progress) failed for %s: %s", source_id, e)

    prompt = f"/guidance-transcript {ticker} transcript {source_id} MODE={mode}"
    log.info("Processing: %s", prompt)
    start = time.monotonic()

    stderr_lines = []

    try:
        options = ClaudeAgentOptions(
            cli_path="/home/faisal/.local/bin/claude",
            setting_sources=["project"],
            cwd=PROJECT_DIR,
            permission_mode="bypassPermissions",
            max_turns=MAX_TURNS,
            max_budget_usd=MAX_BUDGET_USD,
            stderr=lambda line: stderr_lines.append(line),
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
            elif hasattr(msg, "content"):
                log.info("  [%s] %s", type(msg).__name__, msg.content[:200])

        elapsed = time.monotonic() - start

        if result_text is None:
            log.error("No result returned for %s (elapsed: %.0fs)", source_id, elapsed)
            for line in stderr_lines[-20:]:
                log.error("  CLI stderr: %s", line)
            if is_write and mgr:
                try:
                    mark_status(mgr, source_id, "failed")
                except Exception:
                    pass
            return False

        log.info("Completed %s in %.0fs", source_id, elapsed)
        log.info("Result: %s", result_text[:2000])

        if is_write and mgr:
            try:
                mark_status(mgr, source_id, "completed")
                log.info("guidance_status=completed")
            except Exception as e:
                log.warning("mark_status(completed) failed for %s: %s", source_id, e)
        return True

    except Exception as e:
        elapsed = time.monotonic() - start
        log.error("Failed %s after %.0fs", source_id, elapsed, exc_info=True)
        for line in stderr_lines[-20:]:
            log.error("  CLI stderr: %s", line)
        if is_write and mgr:
            try:
                mark_status(mgr, source_id, "failed")
            except Exception:
                pass
        return False


# ---------------------------------------------------------------------------
# Re-queue helper — pushes unprocessed transcripts back to Redis on shutdown
# ---------------------------------------------------------------------------
async def _requeue_remaining(ticker: str, source_ids: list, mode: str):
    """Push unprocessed transcripts back to the queue so they aren't lost."""
    try:
        r = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
        payload = json.dumps({"ticker": ticker, "source_ids": source_ids, "mode": mode})
        await r.lpush(QUEUE_NAME, payload)
        await r.aclose()
        log.info("Re-queued %d transcripts for %s", len(source_ids), ticker)
    except Exception as e:
        log.error("Failed to re-queue remaining transcripts: %s", e)


# ---------------------------------------------------------------------------
# Batch processing — handles both single and multi-transcript payloads
# ---------------------------------------------------------------------------
async def process_item(payload: dict, mgr) -> bool:
    """Process a queue item. Handles single source_id or batch source_ids."""
    ticker = payload.get("ticker", "UNKNOWN")
    mode = payload.get("mode", DEFAULT_MODE)

    # Batch: source_ids list (one company, sequential processing)
    source_ids = payload.get("source_ids")
    if source_ids and isinstance(source_ids, list):
        log.info("Batch: %d transcripts for %s (mode=%s)", len(source_ids), ticker, mode)
        success_count = 0
        for i, sid in enumerate(source_ids, 1):
            if shutdown_event.is_set():
                # Re-queue unprocessed transcripts so they aren't lost
                remaining = source_ids[i - 1:]
                log.info("Shutdown requested at %d/%d — re-queuing %d remaining",
                         i - 1, len(source_ids), len(remaining))
                await _requeue_remaining(ticker, remaining, mode)
                return True  # Already re-queued — don't trigger retry logic
            log.info("Batch [%d/%d]: %s", i, len(source_ids), sid)
            ok = await process_one(ticker, sid, mode, mgr)
            if ok:
                success_count += 1
        log.info("Batch complete: %d/%d succeeded for %s", success_count, len(source_ids), ticker)
        return success_count == len(source_ids)

    # Single: source_id string
    source_id = payload.get("source_id", "")
    if not source_id:
        log.error("Missing source_id/source_ids in payload: %s", payload)
        return False
    return await process_one(ticker, source_id, mode, mgr)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
async def main():
    log.info("=" * 60)
    log.info("Claude Code Worker starting")
    log.info("  Pod: %s", WORKER_POD)
    log.info("  Redis: %s:%s", REDIS_HOST, REDIS_PORT)
    log.info("  Queue: %s", QUEUE_NAME)
    log.info("  MCP Neo4j: %s", MCP_NEO4J_URL)
    log.info("  Max turns: %s, Max budget: $%s", MAX_TURNS, MAX_BUDGET_USD)
    log.info("  Default mode: %s", DEFAULT_MODE)
    log.info("=" * 60)

    # Neo4j connection for ProcessingLog
    mgr = None
    try:
        mgr = get_manager()
        mgr.execute_cypher_query_all("RETURN 1 AS ok")
        log.info("Neo4j connected (ProcessingLog)")
    except Exception as e:
        log.warning("Neo4j connection failed — ProcessingLog disabled: %s", e)
        mgr = None

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
            result = await r.brpop(QUEUE_NAME, timeout=5)
            if result is None:
                continue

            _, raw_payload = result
            payload = parse_payload(raw_payload)
            log.info("Dequeued: %s", json.dumps(payload))

            success = await process_item(payload, mgr)

            if not success:
                retry_count = payload.get("_retry", 0) + 1
                if retry_count <= MAX_RETRIES:
                    payload["_retry"] = retry_count
                    await r.lpush(QUEUE_NAME, json.dumps(payload))
                    log.warning("Re-queued for retry (attempt %d/%d): %s",
                                retry_count, MAX_RETRIES, payload.get("ticker"))
                else:
                    await r.lpush(DEAD_LETTER_QUEUE, json.dumps(payload))
                    log.error("Dead-lettered after %d attempts: %s",
                              retry_count, payload.get("ticker"))

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
    if mgr:
        try:
            mgr.close()
        except Exception:
            pass
    await r.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Interrupted")
