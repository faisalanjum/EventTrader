import httpx
import concurrent.futures
import logging
import sqlite3
import time
from config.feature_flags import CHROMADB_MAX_WORKERS, CHROMADB_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

# Thread pool with configurable workers
_pool = concurrent.futures.ThreadPoolExecutor(
    max_workers=CHROMADB_MAX_WORKERS,
    thread_name_prefix="chromadb-safe"
)

# HTTP transport with retries
_transport = httpx.HTTPTransport(retries=3)
# Limits with keepalive configuration
_limits = httpx.Limits(
    max_keepalive_connections=10, 
    max_connections=20,
    keepalive_expiry=20.0  # Short keepalive to prevent stale connections
)
_http_cfg = dict(transport=_transport, timeout=httpx.Timeout(60), limits=_limits)

def httpx_client():
    """Create httpx client for ChromaDB initialization"""
    return httpx.Client(**_http_cfg)

def safe_chromadb_call(fn, label="call", timeout_seconds=None):
    """Run a ChromaDB op with hard timeout; return None on failure."""
    if timeout_seconds is None:
        timeout_seconds = CHROMADB_TIMEOUT_SECONDS
    
    start = time.time()
    future = _pool.submit(fn)
    try:
        return future.result(timeout=timeout_seconds)
    except concurrent.futures.TimeoutError:
        elapsed = time.time() - start
        logger.warning(f"ChromaDB timeout after {elapsed:.1f}s ({label})")
        return None
    except (sqlite3.OperationalError, ConnectionError) as e:
        logger.warning(f"ChromaDB lock/disconnect ({label}): {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected ChromaDB error ({label}): {e}")
        return None