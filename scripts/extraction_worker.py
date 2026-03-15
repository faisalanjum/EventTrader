#!/usr/bin/env python3
"""Extraction Pipeline Worker — processes extraction jobs from Redis queue.

Listens on Redis queue `extract:pipeline` and runs the /extract skill
via Claude Agent SDK for each incoming payload.

Deployment: K8s `processing` namespace as `extraction-worker`
KEDA: Scales 1->7 based on queue depth

Payload format (JSON) — one message = one job:
  {
      "asset": "transcript",
      "ticker": "AAPL",
      "source_id": "AAPL_2025-01-30T17.00",
      "type": "guidance",
      "mode": "write"
  }

Supported types: discovered from `.claude/skills/extract/types`
Supported assets: transcript, 8k, 10q, 10k, news

Status tracking:
  Sets {type}_status property on the source node (e.g. guidance_status).
  Skipped for mode=dry_run.

File-based result protocol:
  Passes RESULT_PATH to the /extract skill. After SDK completion, reads the
  result JSON file to determine success/failure. Missing or malformed file
  is treated as failure.
"""

import asyncio
import json
import logging
import os
import platform
import signal
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# Project root — must chdir before importing SDK so setting_sources finds .claude/
PROJECT_DIR = "/home/faisal/EventMarketDB"
os.chdir(PROJECT_DIR)
sys.path.insert(0, PROJECT_DIR)
TYPE_ROOT = Path(PROJECT_DIR) / ".claude" / "skills" / "extract" / "types"

import redis.asyncio as aioredis
from claude_agent_sdk import ClaudeAgentOptions, query

from neograph.Neo4jConnection import get_manager

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REDIS_HOST = os.environ.get("REDIS_HOST", "redis.infrastructure.svc.cluster.local")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
QUEUE_NAME = os.environ.get("QUEUE_NAME", "extract:pipeline")
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
# Type whitelist (defense-in-depth)
# ---------------------------------------------------------------------------
def discover_allowed_types():
    """Return extraction types with the minimum contract required by /extract."""
    allowed = set()
    if not TYPE_ROOT.exists():
        return allowed

    for type_dir in TYPE_ROOT.iterdir():
        if not type_dir.is_dir():
            continue

        required = (
            type_dir / "core-contract.md",
            type_dir / "primary-pass.md",
            type_dir / f"{type_dir.name}-queries.md",
        )
        if all(path.exists() for path in required):
            allowed.add(type_dir.name)

    return allowed


ALLOWED_TYPES = discover_allowed_types()

# ---------------------------------------------------------------------------
# Per-type model configuration
# ---------------------------------------------------------------------------
import yaml

def load_type_config(type_name: str) -> dict:
    """Load model config from types/{TYPE}/config.yaml. Returns defaults if missing."""
    config_path = TYPE_ROOT / type_name / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logging.getLogger(__name__).warning("Failed to load %s: %s", config_path, e)
        return {}

def resolve_models(config: dict, asset: str) -> dict:
    """Resolve orchestrator/primary/enrichment models for a type×asset combo."""
    defaults = {
        "orchestrator": config.get("orchestrator", "sonnet"),
        "primary": config.get("primary", "sonnet"),
        "enrichment": config.get("enrichment", "sonnet"),
    }
    asset_overrides = config.get("assets", {}).get(asset, {})
    return {k: asset_overrides.get(k, v) for k, v in defaults.items()}

# ---------------------------------------------------------------------------
# Asset -> Label mapping
# ---------------------------------------------------------------------------
ASSET_LABELS = {
    "transcript": ("Transcript", "t"),
    "8k": ("Report", "r"),
    "10q": ("Report", "r"),
    "10k": ("Report", "r"),
    "news": ("News", "n"),
}

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
        logging.FileHandler(LOG_DIR / "extraction-worker.log"),
    ],
)
# Suppress noisy Neo4j driver warnings
logging.getLogger("neo4j").setLevel(logging.ERROR)
log = logging.getLogger("extraction-worker")

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
# Generalized status tracking
# ---------------------------------------------------------------------------
def mark_status(mgr, asset: str, source_id: str, type_name: str, status: str, error: str = None):
    """Set {type}_status (and optionally {type}_error) on the source node."""
    label, alias = ASSET_LABELS[asset]
    status_prop = f"{type_name}_status"
    query_str = f"MATCH ({alias}:{label} {{id: $sid}}) SET {alias}.{status_prop} = $status"
    params = {"sid": source_id, "status": status}

    if error:
        error_prop = f"{type_name}_error"
        query_str += f", {alias}.{error_prop} = $error"
        params["error"] = error

    query_str += f" RETURN count({alias}) AS affected"

    rows = mgr.execute_cypher_query_all(query_str, params)
    affected = rows[0]["affected"] if rows else 0
    if affected != 1:
        raise RuntimeError(
            f"mark_status({type_name}={status}) affected {affected} rows for {source_id} ({asset})"
        )


# ---------------------------------------------------------------------------
# Payload parsing & validation
# ---------------------------------------------------------------------------
def parse_payload(raw: bytes) -> dict:
    """Parse queue payload — must be a JSON object."""
    text = raw.decode("utf-8").strip()
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except (json.JSONDecodeError, ValueError):
        pass
    raise ValueError(f"Invalid payload (expected JSON object): {text[:200]}")


def validate_payload(payload: dict):
    """Validate required fields and values. Raises ValueError on bad input."""
    missing = []
    for field in ("asset", "ticker", "source_id", "type"):
        if not payload.get(field):
            missing.append(field)
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    type_name = payload["type"]
    if type_name not in ALLOWED_TYPES:
        raise ValueError(f"Disallowed type '{type_name}' — allowed: {ALLOWED_TYPES}")

    asset = payload["asset"]
    if asset not in ASSET_LABELS:
        raise ValueError(f"Unknown asset '{asset}' — allowed: {set(ASSET_LABELS.keys())}")


# ---------------------------------------------------------------------------
# File-based result protocol
# ---------------------------------------------------------------------------
def read_result_file(result_path: str, type_name: str, source_id: str) -> dict:
    """Read and validate the result JSON file. Returns parsed dict or raises."""
    p = Path(result_path)
    if not p.exists():
        raise FileNotFoundError(f"Result file missing: {result_path}")

    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"Malformed result file {result_path}: {e}") from e

    required_fields = {"type", "source_id", "status"}
    present = set(data.keys()) & required_fields
    if present != required_fields:
        missing = required_fields - present
        raise ValueError(f"Result file missing fields {missing}: {result_path}")

    return data


# ---------------------------------------------------------------------------
# Core processing — single extraction job
# ---------------------------------------------------------------------------
async def process_one(
    ticker: str,
    asset: str,
    source_id: str,
    type_name: str,
    mode: str,
    mgr,
) -> bool:
    """Run /extract for a single job. Returns True on success."""
    is_write = mode == "write"

    if is_write and mgr:
        try:
            mark_status(mgr, asset, source_id, type_name, "in_progress")
        except Exception as e:
            log.warning("mark_status(in_progress) failed for %s/%s/%s: %s",
                        type_name, asset, source_id, e)

    # Resolve per-type×asset model configuration
    type_config = load_type_config(type_name)
    models = resolve_models(type_config, asset)
    log.info("Model config for %s/%s: orchestrator=%s primary=%s enrichment=%s",
             type_name, asset, models["orchestrator"], models["primary"], models["enrichment"])

    # Generate unique result file path
    result_path = f"/tmp/extract_result_{type_name}_{source_id}_{uuid.uuid4().hex[:8]}.json"

    prompt = (f"/extract {ticker} {asset} {source_id} TYPE={type_name} MODE={mode}"
              f" PRIMARY_MODEL={models['primary']} ENRICHMENT_MODEL={models['enrichment']}"
              f" RESULT_PATH={result_path}")
    log.info("Processing: %s", prompt)
    start = time.monotonic()

    stderr_lines = []

    try:
        options = ClaudeAgentOptions(
            cli_path="/home/faisal/.local/bin/claude",
            setting_sources=["project"],
            cwd=PROJECT_DIR,
            permission_mode="bypassPermissions",
            model=models["orchestrator"],
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
        result_msg = None
        async for msg in query(prompt=prompt, options=options):
            msg_type = type(msg).__name__
            if msg_type == "SystemMessage" and getattr(msg, "subtype", "") == "init":
                d = msg.data
                log.info("  [Init] model=%s apiKeySource=%s version=%s",
                         d.get("model"), d.get("apiKeySource"), d.get("claude_code_version"))
            elif msg_type == "ResultMessage":
                result_text = msg.result
                result_msg = msg
            elif msg_type == "AssistantMessage":
                log.info("  [%s] model=%s %s", msg_type, msg.model,
                         str(msg.content)[:200])
            elif hasattr(msg, "content"):
                log.info("  [%s] %s", msg_type, str(msg.content)[:200])

        elapsed = time.monotonic() - start

        if result_msg:
            u = result_msg.usage or {}
            log.info("  [Usage] type=%s asset=%s tokens_in=%s cached=%s tokens_out=%s "
                     "cost=$%.4f turns=%d duration=%ds",
                     type_name, asset,
                     u.get("input_tokens", "?"),
                     u.get("cache_read_input_tokens", "?"),
                     u.get("output_tokens", "?"),
                     result_msg.total_cost_usd or 0,
                     result_msg.num_turns,
                     (result_msg.duration_ms or 0) // 1000)

        if result_text is None:
            log.error("No result returned for %s/%s/%s (elapsed: %.0fs)",
                      type_name, asset, source_id, elapsed)
            for line in stderr_lines[-20:]:
                log.error("  CLI stderr: %s", line)
            if is_write and mgr:
                try:
                    mark_status(mgr, asset, source_id, type_name, "failed",
                                error="No result returned from SDK")
                except Exception:
                    pass
            return False

        # --- File-based result protocol ---
        try:
            result_data = read_result_file(result_path, type_name, source_id)
            result_status = result_data.get("status", "unknown")
            log.info("Result file status=%s for %s/%s/%s", result_status, type_name, asset, source_id)

            if is_write and mgr:
                if result_status == "completed":
                    mark_status(mgr, asset, source_id, type_name, "completed")
                    log.info("%s_status=completed for %s", type_name, source_id)
                else:
                    result_error = result_data.get("error", f"Result status: {result_status}")
                    mark_status(mgr, asset, source_id, type_name, "failed", error=result_error)
                    log.warning("%s_status=failed for %s: %s", type_name, source_id, result_error)
                    return False

        except (FileNotFoundError, ValueError) as e:
            log.error("Result file error for %s/%s/%s: %s", type_name, asset, source_id, e)
            if is_write and mgr:
                try:
                    mark_status(mgr, asset, source_id, type_name, "failed",
                                error=str(e))
                except Exception:
                    pass
            return False

        finally:
            # Clean up result file
            try:
                Path(result_path).unlink(missing_ok=True)
            except Exception:
                pass

        log.info("Completed %s/%s/%s in %.0fs", type_name, asset, source_id, elapsed)
        log.info("Result: %s", result_text[:2000])
        return True

    except Exception as e:
        elapsed = time.monotonic() - start
        log.error("Failed %s/%s/%s after %.0fs", type_name, asset, source_id, elapsed, exc_info=True)
        for line in stderr_lines[-20:]:
            log.error("  CLI stderr: %s", line)
        if is_write and mgr:
            try:
                mark_status(mgr, asset, source_id, type_name, "failed", error=str(e))
            except Exception:
                pass
        # Clean up result file on exception too
        try:
            Path(result_path).unlink(missing_ok=True)
        except Exception:
            pass
        return False


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
async def main():
    log.info("=" * 60)
    log.info("Extraction Pipeline Worker starting")
    log.info("  Pod: %s", WORKER_POD)
    log.info("  Redis: %s:%s", REDIS_HOST, REDIS_PORT)
    log.info("  Queue: %s", QUEUE_NAME)
    log.info("  Dead-letter: %s", DEAD_LETTER_QUEUE)
    log.info("  MCP Neo4j: %s", MCP_NEO4J_URL)
    log.info("  Max turns: %s, Max budget: $%s", MAX_TURNS, MAX_BUDGET_USD)
    log.info("  Default mode: %s", DEFAULT_MODE)
    log.info("  Allowed types: %s", ALLOWED_TYPES)
    log.info("  Asset labels: %s", set(ASSET_LABELS.keys()))
    log.info("=" * 60)

    # Neo4j connection for status tracking
    mgr = None
    try:
        mgr = get_manager()
        mgr.execute_cypher_query_all("RETURN 1 AS ok")
        log.info("Neo4j connected (status tracking)")
    except Exception as e:
        log.warning("Neo4j connection failed — status tracking disabled: %s", e)
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

            # Parse payload
            try:
                payload = parse_payload(raw_payload)
            except ValueError as e:
                log.error("Payload parse error: %s", e)
                continue

            log.info("Dequeued: %s", json.dumps(payload))

            # Validate payload
            try:
                validate_payload(payload)
            except ValueError as e:
                log.error("Payload validation error: %s — dead-lettering", e)
                payload["_error"] = str(e)
                payload["_failed_at"] = datetime.utcnow().isoformat() + "Z"
                await r.lpush(DEAD_LETTER_QUEUE, json.dumps(payload))
                continue

            ticker = payload["ticker"]
            asset = payload["asset"]
            source_id = payload["source_id"]
            type_name = payload["type"]
            mode = payload.get("mode", DEFAULT_MODE)

            success = await process_one(ticker, asset, source_id, type_name, mode, mgr)

            if not success:
                retry_count = payload.get("_retry", 0) + 1
                error_message = f"Failed processing {type_name}/{asset}/{source_id}"
                if retry_count <= MAX_RETRIES:
                    payload["_retry"] = retry_count
                    await r.lpush(QUEUE_NAME, json.dumps(payload))
                    log.warning("Re-queued for retry (attempt %d/%d): %s %s/%s",
                                retry_count, MAX_RETRIES, ticker, type_name, asset)
                else:
                    payload["_retry"] = retry_count
                    payload["_error"] = error_message
                    payload["_failed_at"] = datetime.utcnow().isoformat() + "Z"
                    await r.lpush(DEAD_LETTER_QUEUE, json.dumps(payload))
                    log.error("Dead-lettered after %d attempts: %s %s/%s/%s",
                              retry_count, ticker, type_name, asset, source_id)
                    # Also mark as failed on the node
                    if mode == "write" and mgr:
                        try:
                            mark_status(mgr, asset, source_id, type_name, "failed",
                                        error=f"Exhausted {MAX_RETRIES} retries")
                        except Exception:
                            pass

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
