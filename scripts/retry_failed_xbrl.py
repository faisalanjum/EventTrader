#!/usr/bin/env python
"""
Retry Failed XBRL Documents
--------------------------
Script to requeue failed XBRL documents for processing by resetting their status
and pushing them back to the appropriate XBRL worker queues.
"""

import os
import sys
import logging
import json
from neo4j import GraphDatabase
from pathlib import Path
from dotenv import load_dotenv
import warnings

# Add parent directory to path to import Redis classes
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from redisDB.redisClasses import RedisClient
from redisDB.redis_constants import RedisKeys

# Suppress Neo4j warnings
warnings.filterwarnings('ignore', category=UserWarning, module='neo4j')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Load environment variables
script_dir = Path(__file__).resolve().parent
workspace_dir = script_dir.parent
env_file = workspace_dir / '.env'

if env_file.exists():
    load_dotenv(env_file, override=True)
else:
    logger.error(f".env file not found at {env_file}")
    sys.exit(1)

# Neo4j connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

def connect_to_neo4j():
    """Connect to Neo4j database"""
    try:
        driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        logger.info(f"Successfully connected to Neo4j at {NEO4J_URI}")
        return driver
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        sys.exit(1)

def get_redis_client():
    """Get Redis client instance"""
    return RedisClient(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        prefix='',
        source_type=RedisKeys.SOURCE_REPORTS
    )

def get_failed_xbrl_documents(driver, form_type=None, limit=None):
    """Get failed XBRL documents from Neo4j"""
    query = """
    MATCH (r:Report {xbrl_status: 'FAILED'})
    WHERE r.is_xml = true AND r.cik IS NOT NULL
    """
    
    if form_type:
        query += f" AND r.formType = '{form_type}'"
    
    query += """
    RETURN r.accessionNo AS accession,
           r.cik AS cik,
           r.formType AS form_type,
           r.id AS report_id,
           r.xbrl_error AS error
    ORDER BY r.filedAt DESC
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    with driver.session() as session:
        try:
            result = session.run(query)
            documents = []
            for record in result:
                documents.append({
                    'accession': record['accession'],
                    'cik': record['cik'],
                    'form_type': record['form_type'],
                    'report_id': record['report_id'],
                    'error': record['error']
                })
            return documents
        except Exception as e:
            logger.error(f"Error querying Neo4j: {e}")
            return []

def reset_xbrl_status(driver, report_ids):
    """Reset xbrl_status to NULL and clear xbrl_error for given reports"""
    query = """
    UNWIND $report_ids AS report_id
    MATCH (r:Report {id: report_id})
    SET r.xbrl_status = NULL,
        r.xbrl_error = NULL
    RETURN count(r) AS updated_count
    """
    
    with driver.session() as session:
        try:
            result = session.run(query, report_ids=report_ids)
            record = result.single()
            return record['updated_count']
        except Exception as e:
            logger.error(f"Error updating Neo4j: {e}")
            return 0

def determine_queue(form_type):
    """Determine which XBRL queue to use based on form type"""
    if not form_type or not form_type.strip():
        return RedisKeys.XBRL_QUEUE_HEAVY  # Default to heavy for safety
    elif form_type in {"10-K", "10-K/A"}:
        return RedisKeys.XBRL_QUEUE_HEAVY
    elif form_type in {"10-Q", "10-Q/A"}:
        return RedisKeys.XBRL_QUEUE_MEDIUM
    else:
        # return RedisKeys.XBRL_QUEUE_LIGHT  # DISABLED: Light queue removed
        return None  # Skip all other forms

def main():
    """Main function to retry failed XBRL documents"""
    logger.info("Starting Failed XBRL Document Retry")
    
    # Parse command line arguments
    form_type_filter = None
    limit = None
    
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith("--form-type="):
                form_type_filter = arg.split("=")[1]
            elif arg.startswith("--limit="):
                try:
                    limit = int(arg.split("=")[1])
                except ValueError:
                    logger.error("Invalid limit value")
                    sys.exit(1)
            elif arg == "--help":
                print("Usage: python retry_failed_xbrl.py [--form-type=TYPE] [--limit=N]")
                print("\nOptions:")
                print("  --form-type=TYPE  Only retry documents of specific form type (e.g., 10-K)")
                print("  --limit=N        Only retry first N documents")
                print("\nExamples:")
                print("  python retry_failed_xbrl.py                    # Retry all failed")
                print("  python retry_failed_xbrl.py --form-type=10-K   # Only 10-K forms")
                print("  python retry_failed_xbrl.py --limit=10         # Only first 10")
                return
    
    # Connect to Neo4j and Redis
    neo4j_driver = connect_to_neo4j()
    redis_client = get_redis_client()
    
    try:
        # Get failed documents
        failed_docs = get_failed_xbrl_documents(neo4j_driver, form_type_filter, limit)
        
        if not failed_docs:
            print("\n✅ No failed XBRL documents found to retry!")
            return
        
        # Display documents to be retried
        print(f"\n===== Found {len(failed_docs)} Failed Documents =====")
        print(f"\n{'Accession':<22} {'CIK':<12} {'Form':<8} {'Queue':<20} {'Error'}")
        print("-" * 100)
        
        queue_counts = {"heavy": 0, "medium": 0, "light": 0}
        
        for doc in failed_docs:
            queue = determine_queue(doc['form_type'])
            if queue is None:
                logger.info(f"Skipping {doc['accession']} - form type {doc['form_type']} not configured for XBRL")
                continue
            queue_type = queue.split(":")[-1]  # Extract 'heavy', 'medium', or 'light'
            queue_counts[queue_type] += 1
            
            error_msg = (doc['error'] or 'No error message')[:40]
            print(f"{doc['accession']:<22} {doc['cik']:<12} {doc['form_type']:<8} {queue_type:<20} {error_msg}")
        
        # Show queue distribution
        print(f"\n===== Queue Distribution =====")
        print(f"Heavy queue:  {queue_counts['heavy']} documents")
        print(f"Medium queue: {queue_counts['medium']} documents")
        print(f"Light queue:  {queue_counts['light']} documents")
        
        # Confirm retry
        confirm = input("\n\nProceed with retrying these documents? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Retry cancelled.")
            return
        
        # Reset status in Neo4j
        report_ids = [doc['report_id'] for doc in failed_docs]
        updated_count = reset_xbrl_status(neo4j_driver, report_ids)
        print(f"\n✅ Reset xbrl_status for {updated_count} documents in Neo4j")
        
        # Queue documents for reprocessing
        queued_count = 0
        for doc in failed_docs:
            queue = determine_queue(doc['form_type'])
            if queue is None:
                logger.info(f"Skipping {doc['accession']} - form type {doc['form_type']} not configured for XBRL")
                continue
            job_data = {
                "report_id": doc['report_id'],
                "accession": doc['accession'],
                "cik": doc['cik'],
                "form_type": doc['form_type']
            }
            
            try:
                redis_client.push_to_queue(queue, json.dumps(job_data))
                queued_count += 1
            except Exception as e:
                logger.error(f"Failed to queue {doc['accession']}: {e}")
        
        print(f"✅ Queued {queued_count} documents for reprocessing")
        
        # Show queue lengths
        print("\n===== Current Queue Lengths =====")
        for queue_type in ["heavy", "medium", "light"]:
            queue_name = f"{RedisKeys.SOURCE_REPORTS}:queues:xbrl:{queue_type}"
            try:
                length = redis_client.client.llen(queue_name)
                print(f"{queue_type.capitalize()} queue: {length} items")
            except Exception as e:
                logger.error(f"Error checking queue {queue_name}: {e}")
                
    finally:
        neo4j_driver.close()
        logger.info("Failed XBRL Document Retry completed")

if __name__ == "__main__":
    main()