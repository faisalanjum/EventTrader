"""
Quick stats for EventTrader's Redis + Neo4j.

Run:
    python redis_stats.py               # stand-alone
or call  redis_stats.run_all()          # from anywhere (e.g. run_event_trader.py)
"""

import os, json, logging
from datetime import datetime
from typing import Set, Tuple

# Setup logger - use standard module logger
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Redis helper – uses the *same* RedisClient class EventTrader uses #
# ------------------------------------------------------------------ #
from .redisClasses import RedisClient, RedisKeys         

def _get_redis() -> RedisClient:
    # honour REDIS_HOST / REDIS_PORT if they exist, otherwise fall back
    # to the defaults that have always worked on the server.
    from eventtrader.keys import REDIS_HOST, REDIS_PORT  # Import the constants for consistency
    client = RedisClient(
        host=os.getenv("REDIS_HOST", REDIS_HOST),
        port=int(os.getenv("REDIS_PORT", REDIS_PORT)),
        prefix=""  # keep the admin-level prefix
    )
    logger.debug(f"Redis client initialized with host={client.host}, port={client.port}")
    return client



def _gather_ids(r_cli, source: str) -> Tuple[Set[str], Set[str], Set[str], int]:
    """
    Returns three *sets* of full meta keys (e.g. tracking:meta:news:<id>):
        inserted_ids, filtered_ids, failed_ids
    """
    match_pat = f"tracking:meta:{source}:*"
    inserted, filtered, failed = set(), set(), set()
    total_keys = 0
    
    logger.debug(f"Scanning Redis for pattern: {match_pat}")
    for k in r_cli.client.scan_iter(match_pat):
        total_keys += 1
        if r_cli.client.hexists(k, "inserted_into_neo4j_at"):
            inserted.add(k)
        if r_cli.client.hexists(k, "filtered_at"):
            filtered.add(k)
        if r_cli.client.hexists(k, "failed_at"):
            failed.add(k)

    logger.debug(f"Found {total_keys} keys matching pattern {match_pat}")
    return inserted, filtered, failed, total_keys


# ----------------------------------------------------------- #
#  Neo4j helper – uses the singleton manager EventTrader uses #
# ----------------------------------------------------------- #
from neograph.Neo4jConnection import get_manager
neo = get_manager()            # already configured through .env

def _neo_counts() -> Tuple[int, int, int]:
    logger.debug("Querying Neo4j for node counts...")
    cypher = (
        "RETURN "
        "COUNT { MATCH (n:News) RETURN n }  AS news_cnt, "
        "COUNT { MATCH (n:Report) RETURN n } AS rpt_cnt, "
        "COUNT { MATCH (n:Transcript) RETURN n } AS trn_cnt"
    )
    rec = neo.execute_cypher_query(cypher, parameters={})
    return rec["news_cnt"], rec["rpt_cnt"], rec["trn_cnt"]


# ------------------------------- #
#  Public, user-facing functions  #
# ------------------------------- #
def analyze(source: str) -> None:
    """Print a one-page report for 'news', 'reports' or 'transcripts'."""
    logger.info(f"Analyzing Redis stats for source: {source}")
    r_cli = _get_redis()
    
    inserted, filtered, failed, total_keys = _gather_ids(r_cli, source)
    ff_union  = filtered | failed
    overlap   = inserted & ff_union
    total     = len(inserted | filtered | failed)     # ← corrected

    # Using a format consistent with other scripts
    logger.info(f"--- {source.upper()} STATS ---")
    logger.info(f"Total scanned keys (all):                     {total_keys:>6}")    
    logger.info(f"Filtered or Failed:                           {len(ff_union):>6}")
    logger.info(f"Inserted into Neo4j:                          {len(inserted):>6}")
    logger.info(f"Filtered_or_Failed ∩ Inserted_into_Neo4j:     {len(overlap):>6}")
    logger.info(f"Filtered ∩ Failed:                            {len(filtered & failed):>6}")
    logger.info(f"Final status keys (inserted, filtered, or failed):     {total:>6}")

    

def run_all() -> None:
    """Run analysis for all sources and show Neo4j counts."""
    logger.info("Starting Redis and Neo4j stats analysis")
    for src in ("news", "reports", "transcripts"):
        analyze(src)

    try:
        n, r, t = _neo_counts()
        logger.info("--- NEO4J NODE COUNTS ---")
        logger.info(f"News nodes:       {n}")
        logger.info(f"Report nodes:     {r}")
        logger.info(f"Transcript nodes: {t}")
    except Exception as e:
        logger.error(f"Error retrieving Neo4j counts: {e}", exc_info=True)
    
    logger.info("Redis and Neo4j stats analysis completed")


# ---------- #
#  CLI hook  #
# ---------- #
if __name__ == "__main__":
    # Setup console logging for CLI mode
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    import sys
    if len(sys.argv) == 2 and sys.argv[1] in {"news","reports","transcripts"}:
        analyze(sys.argv[1])
    else:
        run_all()
