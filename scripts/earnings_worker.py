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

ProcessingLog:
  For mode=write, writes a ProcessingLog node to Neo4j before/after each transcript.
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
from datetime import datetime, timezone
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
RETRY_QUEUE = f"{QUEUE_NAME}:retry"
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
# ProcessingLog — Neo4j ledger
# ---------------------------------------------------------------------------
def log_start(mgr, source_id: str, source_type: str, task: str, mode: str):
    """Write ProcessingLog(in_progress) before processing."""
    mgr.execute_cypher_query_all(
        "MERGE (p:ProcessingLog {source_id: $sid, task: $task}) "
        "SET p.source_type = $stype, p.status = 'in_progress', "
        "    p.started_at = datetime(), p.completed_at = null, "
        "    p.error = null, p.items_written = null, "
        "    p.mode = $mode, p.worker_pod = $pod "
        "WITH p "
        "MATCH (t {id: $sid}) WHERE $stype IN labels(t) "
        "MERGE (p)-[:FOR_SOURCE]->(t)",
        {"sid": source_id, "task": task, "stype": source_type, "mode": mode, "pod": WORKER_POD},
    )


def log_complete(mgr, source_id: str, task: str, items_written: int):
    """Update ProcessingLog to completed."""
    mgr.execute_cypher_query_all(
        "MATCH (p:ProcessingLog {source_id: $sid, task: $task}) "
        "SET p.status = 'completed', p.completed_at = datetime(), "
        "    p.items_written = $items",
        {"sid": source_id, "task": task, "items": items_written},
    )


def log_failed(mgr, source_id: str, task: str, error: str):
    """Update ProcessingLog to failed."""
    mgr.execute_cypher_query_all(
        "MATCH (p:ProcessingLog {source_id: $sid, task: $task}) "
        "SET p.status = 'failed', p.completed_at = datetime(), "
        "    p.error = $error, p.items_written = 0",
        {"sid": source_id, "task": task, "error": error[:500]},
    )


def extract_item_count(result_text: str) -> int:
    """Best-effort extraction of items_written from the result summary."""
    import re
    # Match patterns like "17 guidance items" or "Items extracted: 18"
    for pattern in [r"(\d+)\s+guidance\s+items?", r"(\d+)\s+items?\s+extracted",
                    r"items?\s*(?:extracted|written)[:\s]*(\d+)", r"(\d+)\s+items?\s+.*?written"]:
        m = re.search(pattern, result_text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return 0


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
    task_name = "guidance_extraction"
    is_write = mode == "write"

    if is_write:
        try:
            log_start(mgr, source_id, "Transcript", task_name, mode)
        except Exception as e:
            log.warning("ProcessingLog start failed for %s: %s", source_id, e)

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
            if is_write:
                try:
                    log_failed(mgr, source_id, task_name, "No result returned from SDK")
                except Exception:
                    pass
            return False

        log.info("Completed %s in %.0fs", source_id, elapsed)
        log.info("Result: %s", result_text[:500])

        if is_write:
            try:
                items = extract_item_count(result_text)
                log_complete(mgr, source_id, task_name, items)
                log.info("ProcessingLog: completed, items_written=%d", items)
            except Exception as e:
                log.warning("ProcessingLog complete failed for %s: %s", source_id, e)
        return True

    except Exception as e:
        elapsed = time.monotonic() - start
        log.error("Failed %s after %.0fs", source_id, elapsed, exc_info=True)
        if is_write:
            try:
                log_failed(mgr, source_id, task_name, str(e))
            except Exception:
                pass
        return False


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
                log.info("Shutdown requested — stopping batch at %d/%d", i - 1, len(source_ids))
                break
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
                    await r.lpush(RETRY_QUEUE, json.dumps(payload))
                    log.warning("Retry queue (attempt %d/%d): %s",
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
