from dotenv import load_dotenv
load_dotenv(override=False)

import os
import time
import json
import logging
import signal
import sys
from typing import Optional

# Add parent directory to path to import log_config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.log_config import setup_logging

# Redis imports
from redisDB.redisClasses import RedisClient
from redisDB.redis_constants import RedisKeys

# Add fallback for older versions of RedisKeys that might not have XBRL_QUEUE
# if not hasattr(RedisKeys, 'XBRL_QUEUE'):
#     setattr(RedisKeys, 'XBRL_QUEUE', f"{RedisKeys.SOURCE_REPORTS}:queues:xbrl")

# Neo4j imports
from neograph.Neo4jConnection import get_manager
from neograph.Neo4jManager import Neo4jManager

# XBRL processor import
from XBRL.xbrl_processor import process_report

# Setup centralized logging
queue_name = os.getenv("XBRL_QUEUE", "unknown")
# Extract worker type from queue name (e.g., "reports:queues:xbrl:heavy" -> "xbrl-heavy")
if "heavy" in queue_name:
    log_prefix = "xbrl-heavy"
elif "medium" in queue_name:
    log_prefix = "xbrl-medium"
elif "light" in queue_name:
    log_prefix = "xbrl-light"
else:
    log_prefix = "xbrl-worker"

setup_logging(name=log_prefix)
logger = logging.getLogger(__name__)

def main():
    
    # Graceful shutdown handler
    def handle_sigterm(*args):
        logger.info("Received termination signal, shutting down gracefully...")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    # Initialize Redis client using the same pattern as elsewhere
    redis_client = RedisClient(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        prefix='',  # No prefix needed for direct queue access
        source_type=RedisKeys.SOURCE_REPORTS
    )
    
    # Get Neo4j singleton manager for database operations
    neo4j_manager = get_manager()
    
    logger.info("[Kube]: XBRL Worker started, waiting for jobs...")

    # Self-exit config (env-var-gated; default OFF → identical to prior behavior).
    # Purpose: recycle the process after N jobs to return accumulated Arelle caches
    # to the OS, preventing same-CIK backfill accumulation OOMs. Kubelet restarts
    # the pod automatically; in-flight jobs are never interrupted (check fires only
    # at top-of-loop, before BRPOP).
    self_exit_enabled = os.getenv("SELF_EXIT_ENABLED", "false").lower() == "true"
    job_count_threshold = int(os.getenv("JOB_COUNT_THRESHOLD", "20"))
    jobs_started = 0
    if self_exit_enabled:
        logger.info(f"[SELF-EXIT] enabled: will exit after {job_count_threshold} jobs for fresh pod")

    while True:
        # Self-exit check — fires only between jobs, never mid-processing.
        if self_exit_enabled and jobs_started >= job_count_threshold:
            logger.info(f"[SELF-EXIT] processed {jobs_started} jobs (threshold={job_count_threshold}); exiting cleanly")
            sys.exit(0)

        # Use the proper queue name from RedisKeys constants
        # queue_result = redis_client.pop_from_queue(RedisKeys.XBRL_QUEUE, timeout=3)
        queue_name = os.getenv("XBRL_QUEUE") # This is the queue name from the Kubernetes environment variable
        queue_result = redis_client.pop_from_queue(queue_name, timeout=3)
        logger.info(f"[Kube]: Polled from queue {queue_name}: {queue_result}")

        
        if not queue_result:
            time.sleep(1)
            continue

        try:
            _, job_json = queue_result  # BRPOP returns [queue_name, value]
        except Exception as e:
            logger.error(f"[ERROR] Unexpected queue result format: {queue_result} | Error: {e}")
            continue

        processor = None
        
        try:
            job_data = json.loads(job_json)
            report_id = job_data.get("report_id")
            accession = job_data.get("accession")
            cik = job_data.get("cik")
            form_type = job_data.get("form_type")
            
            # Defensive check for malformed jobs
            if not accession or not cik or not report_id:
                logger.warning(f"Malformed job skipped: {job_data}")
                continue
            
            # Log job received
            logger.info(f"[Kube]: Processing XBRL job: accession={accession}, cik={cik}, form_type={form_type}")
            
            # Check if already completed (matching local processing behavior)
            with neo4j_manager.driver.session() as session:
                result = session.run(
                    "MATCH (r:Report {id: $id}) RETURN r.xbrl_status AS status",
                    id=report_id
                ).single()
                
                if result and result["status"] in ["COMPLETED", "SKIPPED", "REFERENCE_ONLY"]:
                    logger.info(f"[Kube]: Report {accession} already {result['status']}, skipping")
                    continue
            
            # Update report status to PROCESSING
            with neo4j_manager.driver.session() as session:
                def update_processing_status(tx):
                    tx.run(
                        "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status",
                        id=report_id, status="PROCESSING"
                    )
                session.execute_write(update_processing_status)

            jobs_started += 1  # count jobs that reached processing state (for SELF-EXIT threshold)

            # Process the report
            # Instead of invoking a subprocess, directly process using the class
            start_time = time.time()
            processor = process_report(
                neo4j=neo4j_manager,
                cik=cik,
                accessionNo=accession,
                testing=False
            )

            # Self-healing retry for silent Arelle failures (e.g. SEC 503 that didn't raise).
            # Existing load_xbrl retry only fires on raised exceptions; this catches the
            # "finished successfully but built zero facts" case.
            SILENT_RETRY_MAX = 2
            SILENT_RETRY_DELAY_S = 60
            for silent_retry in range(SILENT_RETRY_MAX):
                facts_so_far = len(processor.facts) if processor and processor.facts else 0
                if facts_so_far > 0:
                    break
                logger.warning(
                    f"[Kube]: 0 facts for {accession} (silent failure) — "
                    f"retry {silent_retry + 1}/{SILENT_RETRY_MAX} after {SILENT_RETRY_DELAY_S}s"
                )
                time.sleep(SILENT_RETRY_DELAY_S)
                try:
                    if processor:
                        processor.close_resources()
                except Exception:
                    pass
                processor = process_report(
                    neo4j=neo4j_manager,
                    cik=cik,
                    accessionNo=accession,
                    testing=False
                )

            # Classify final outcome based on in-memory fact count
            from neograph.xbrl_status_helper import classify_xbrl_run
            final_status, final_error = classify_xbrl_run(processor)

            with neo4j_manager.driver.session() as session:
                def update_status(tx):
                    tx.run(
                        "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
                        id=report_id, status=final_status, error=final_error
                    )
                session.execute_write(update_status)

            # Log completion with timing information
            elapsed = time.time() - start_time
            mins, secs = divmod(int(elapsed), 60)
            facts_final = len(processor.facts) if processor and processor.facts else 0
            logger.info(
                f"[Kube]: {final_status} XBRL for accession: {accession} "
                f"in {mins}m {secs}s (facts={facts_final})"
            )
            
            # Add delay after processing for resource cleanup, matching original behavior
            time.sleep(3)  # 3 second delay to allow for resource cleanup
            
        except Exception as e:
            logger.error(f"[Kube]: Error processing XBRL job: {e}", exc_info=True)
            
            # Update status to FAILED
            try:
                with neo4j_manager.driver.session() as session:
                    def update_failed_status(tx):
                        tx.run(
                            "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status, r.xbrl_error = $error",
                            id=report_id, status="FAILED", error=str(e)[:255]  # Limit error message length
                        )
                    session.execute_write(update_failed_status)
            except Exception as inner_e:
                logger.error(f"[Kube]: Error updating failure status: {inner_e}")
        
        finally:
            # Explicit cleanup of processor resources to prevent memory leaks
            if processor:
                try:
                    processor.close_resources()
                    logger.info(f"[Kube]: Cleaned up resources for {accession if 'accession' in locals() else 'unknown job'}")
                except Exception as cleanup_e:
                    logger.warning(f"[Kube]: Cleanup failed: {cleanup_e}")

if __name__ == "__main__":
    main()