from dotenv import load_dotenv
load_dotenv(override=False)

import os
import time
import json
import logging
import signal
import sys
from typing import Optional

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

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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
    
    while True:
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
            
            # Update report status to PROCESSING
            with neo4j_manager.driver.session() as session:
                def update_processing_status(tx):
                    tx.run(
                        "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status",
                        id=report_id, status="PROCESSING"
                    )
                session.execute_write(update_processing_status)
            
            # Process the report
            # Instead of invoking a subprocess, directly process using the class
            start_time = time.time()
            processor = process_report(
                neo4j=neo4j_manager,
                cik=cik,
                accessionNo=accession,
                testing=False
            )
            
            # Update status to COMPLETED
            with neo4j_manager.driver.session() as session:
                def update_completed_status(tx):
                    tx.run(
                        "MATCH (r:Report {id: $id}) SET r.xbrl_status = $status",
                        id=report_id, status="COMPLETED"
                    )
                session.execute_write(update_completed_status)
            
            # Log completion with timing information
            elapsed = time.time() - start_time
            mins, secs = divmod(int(elapsed), 60)
            logger.info(f"[Kube]: Successfully processed XBRL for accession: {accession} in {mins}m {secs}s")
            
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