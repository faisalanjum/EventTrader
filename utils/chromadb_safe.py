import concurrent.futures, logging, sqlite3
logger = logging.getLogger(__name__)
_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4,
                                              thread_name_prefix="chromadb-safe")

def safe_chromadb_call(fn, timeout_seconds: int = 10):
    """Run a ChromaDB op with hard timeout; return None on failure."""
    future = _pool.submit(fn)
    try:
        return future.result(timeout=timeout_seconds)
    except (concurrent.futures.TimeoutError,
            sqlite3.OperationalError,
            ConnectionError) as e:
        logger.warning(f"ChromaDB timeout/lock: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected ChromaDB error: {e}")
        return None