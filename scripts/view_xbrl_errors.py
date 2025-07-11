#!/usr/bin/env python3
"""
View summary of XBRL processing errors and status
"""

import os
import sys
from pathlib import Path
import logging
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neograph.Neo4jConnection import get_manager
from utils.log_config import setup_logging

# Setup logging
setup_logging(name="view_xbrl_errors")
logger = logging.getLogger(__name__)

def get_xbrl_status_summary():
    """Get overall XBRL processing status summary"""
    
    neo4j = get_manager()
    
    query = """
    MATCH (r:Report)
    WITH r.xbrl_status as status, COUNT(r) as count
    ORDER BY count DESC
    RETURN status, count
    """
    
    with neo4j.driver.session() as session:
        result = session.run(query)
        statuses = [(record['status'] or 'NULL', record['count']) for record in result]
        
        total = sum(count for _, count in statuses)
        
        logger.info("\n=== XBRL Processing Status Summary ===")
        logger.info(f"Total reports: {total:,}")
        logger.info("\nStatus breakdown:")
        for status, count in statuses:
            percentage = (count / total * 100) if total > 0 else 0
            logger.info(f"  {status}: {count:,} ({percentage:.1f}%)")

def get_error_summary():
    """Get summary of XBRL errors grouped by type"""
    
    neo4j = get_manager()
    
    query = """
    MATCH (r:Report)
    WHERE r.xbrl_status = "FAILED"
    WITH r.xbrl_error as error, 
         COUNT(r) as count,
         COLLECT(DISTINCT r.formType)[..5] as sample_forms,
         COLLECT(r.accessionNo)[..3] as sample_reports
    ORDER BY count DESC
    RETURN error, count, sample_forms, sample_reports
    """
    
    with neo4j.driver.session() as session:
        result = session.run(query)
        errors = list(result)
        
        if not errors:
            logger.info("\n✅ No XBRL processing failures found!")
            return
        
        logger.info("\n=== XBRL Error Summary ===")
        total_failures = sum(record['count'] for record in errors)
        logger.info(f"Total failed reports: {total_failures:,}")
        
        logger.info("\nError breakdown:")
        for record in errors:
            error = record['error'] or 'Unknown error'
            count = record['count']
            forms = record['sample_forms']
            samples = record['sample_reports']
            
            logger.info(f"\n{error}")
            logger.info(f"  Count: {count:,}")
            logger.info(f"  Form types: {', '.join(forms)}")
            logger.info(f"  Sample reports: {', '.join(samples[:2])}")

def get_recoverable_failures():
    """Analyze which failures are recoverable"""
    
    neo4j = get_manager()
    
    # Check missing CIK reports that have entities
    missing_cik_query = """
    MATCH (r:Report)
    WHERE r.xbrl_error = "Report is missing CIK"
    AND r.entities IS NOT NULL
    RETURN COUNT(r) as recoverable_cik
    """
    
    # Check deadlock errors
    deadlock_query = """
    MATCH (r:Report)
    WHERE r.xbrl_error CONTAINS "deadlock detected"
    RETURN COUNT(r) as deadlock_count
    """
    
    # Check reports stuck in processing
    stuck_query = """
    MATCH (r:Report)
    WHERE r.xbrl_status = "PROCESSING"
    RETURN COUNT(r) as stuck_count
    """
    
    with neo4j.driver.session() as session:
        cik_result = session.run(missing_cik_query)
        recoverable_cik = cik_result.single()['recoverable_cik']
        
        deadlock_result = session.run(deadlock_query)
        deadlock_count = deadlock_result.single()['deadlock_count']
        
        stuck_result = session.run(stuck_query)
        stuck_count = stuck_result.single()['stuck_count']
        
        logger.info("\n=== Recoverable Failures ===")
        logger.info(f"Missing CIK (with entities available): {recoverable_cik:,}")
        logger.info(f"Deadlock errors (retryable): {deadlock_count:,}")
        logger.info(f"Stuck in PROCESSING: {stuck_count:,}")
        
        total_recoverable = recoverable_cik + deadlock_count
        logger.info(f"\nTotal recoverable failures: {total_recoverable:,}")
        
        if total_recoverable > 0:
            logger.info("\n💡 Run ./scripts/fix_xbrl_failures.py to fix these issues")

def check_queue_health():
    """Check the health of XBRL processing queues"""
    
    neo4j = get_manager()
    
    # Check queued reports by form type
    queue_query = """
    MATCH (r:Report)
    WHERE r.xbrl_status = "QUEUED"
    WITH r.formType as formType, COUNT(r) as count
    ORDER BY count DESC
    RETURN formType, count
    """
    
    with neo4j.driver.session() as session:
        result = session.run(queue_query)
        queued = list(result)
        
        if queued:
            total_queued = sum(record['count'] for record in queued)
            logger.info(f"\n=== Queue Status ===")
            logger.info(f"Total queued: {total_queued:,}")
            logger.info("\nBy form type:")
            for record in queued:
                logger.info(f"  {record['formType']}: {record['count']:,}")

def main():
    """View XBRL error summary"""
    
    # Set environment variables
    os.environ['NEO4J_URI'] = 'bolt://localhost:30687'
    os.environ['NEO4J_USERNAME'] = 'neo4j'
    os.environ['NEO4J_PASSWORD'] = 'Next2020#'
    
    logger.info("XBRL Processing Error Analysis")
    logger.info("=" * 50)
    
    # Get overall status
    get_xbrl_status_summary()
    
    # Get error details
    get_error_summary()
    
    # Check recoverable failures
    get_recoverable_failures()
    
    # Check queue health
    check_queue_health()

if __name__ == "__main__":
    main()