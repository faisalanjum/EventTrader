#!/usr/bin/env python
"""
Find Failed XBRL Documents
-------------------------
Script to query Neo4j for all Report nodes where xbrl_status = 'FAILED' and display
information about the failures including error messages.
"""

import os
import sys
import logging
from collections import Counter, defaultdict
from datetime import datetime
import pandas as pd
from neo4j import GraphDatabase
from pathlib import Path
from dotenv import load_dotenv
import warnings

# Suppress Neo4j warnings about unknown properties
warnings.filterwarnings('ignore', category=UserWarning, module='neo4j')

# Configure logging to stderr so it doesn't interfere with stdout output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Ensure we're loading from the correct .env file
script_dir = Path(__file__).resolve().parent
workspace_dir = script_dir.parent
env_file = workspace_dir / '.env'

# Clear any cached environment variables for Neo4j
for key in ['NEO4J_URI', 'NEO4J_USERNAME', 'NEO4J_PASSWORD', 'NEO4J_USER']:
    if key in os.environ:
        del os.environ[key]

# Load environment variables from the specific .env file
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

def get_failed_xbrl_summary(driver):
    """Get summary statistics of failed XBRL documents"""
    query = """
    MATCH (r:Report {xbrl_status: 'FAILED'})
    RETURN count(r) AS total_failed,
           count(DISTINCT r.formType) AS unique_form_types,
           collect(DISTINCT r.formType) AS form_types
    """
    
    with driver.session() as session:
        try:
            result = session.run(query)
            record = result.single()
            return {
                'total_failed': record['total_failed'],
                'unique_form_types': record['unique_form_types'],
                'form_types': sorted(record['form_types'])
            }
        except Exception as e:
            logger.error(f"Error querying Neo4j: {e}")
            return None

def get_failed_xbrl_details(driver, limit=None):
    """Get detailed information about failed XBRL documents"""
    query = """
    MATCH (r:Report {xbrl_status: 'FAILED'})
    RETURN r.accessionNo AS accession,
           r.cik AS cik,
           r.formType AS form_type,
           r.filedAt AS filed_at,
           r.xbrl_error AS error,
           r.is_xml AS is_xml,
           r.primaryDocumentUrl AS url
    ORDER BY r.filedAt DESC
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    with driver.session() as session:
        try:
            result = session.run(query)
            failed_docs = []
            for record in result:
                failed_docs.append({
                    'accession': record['accession'],
                    'cik': record['cik'],
                    'form_type': record['form_type'],
                    'filed_at': record['filed_at'],
                    'error': record['error'],
                    'is_xml': record['is_xml'],
                    'url': record['url']
                })
            return failed_docs
        except Exception as e:
            logger.error(f"Error querying Neo4j: {e}")
            return []

def get_failed_by_error_type(driver):
    """Group failed documents by error message"""
    query = """
    MATCH (r:Report {xbrl_status: 'FAILED'})
    RETURN r.xbrl_error AS error_message, 
           count(r) AS count,
           collect(DISTINCT r.formType) AS form_types
    ORDER BY count DESC
    """
    
    with driver.session() as session:
        try:
            result = session.run(query)
            error_groups = []
            for record in result:
                error_groups.append({
                    'error_message': record['error_message'] or 'No error message',
                    'count': record['count'],
                    'form_types': sorted(record['form_types'])
                })
            return error_groups
        except Exception as e:
            logger.error(f"Error querying Neo4j: {e}")
            return []

def get_failed_by_form_type(driver):
    """Get failed document count by form type"""
    query = """
    MATCH (r:Report {xbrl_status: 'FAILED'})
    RETURN r.formType AS form_type, count(r) AS count
    ORDER BY count DESC
    """
    
    with driver.session() as session:
        try:
            result = session.run(query)
            form_type_counts = []
            for record in result:
                form_type_counts.append({
                    'form_type': record['form_type'],
                    'count': record['count']
                })
            return form_type_counts
        except Exception as e:
            logger.error(f"Error querying Neo4j: {e}")
            return []

def format_error_message(error_msg, max_length=80):
    """Format error message for display"""
    if not error_msg:
        return "No error message"
    if len(error_msg) <= max_length:
        return error_msg
    return error_msg[:max_length-3] + "..."

def main():
    """Main function to run the script"""
    logger.info("Starting Failed XBRL Documents Report")
    
    # Connect to Neo4j
    driver = connect_to_neo4j()
    
    try:
        # Get summary statistics
        summary = get_failed_xbrl_summary(driver)
        
        if not summary or summary['total_failed'] == 0:
            print("\n✅ No failed XBRL documents found!")
            return
        
        # Print summary
        print("\n===== Failed XBRL Documents Summary =====")
        print(f"Total Failed Documents: {summary['total_failed']}")
        print(f"Unique Form Types: {summary['unique_form_types']}")
        print(f"Form Types: {', '.join(summary['form_types'])}")
        
        # Get failed documents by form type
        print("\n===== Failed Documents by Form Type =====")
        form_type_counts = get_failed_by_form_type(driver)
        for item in form_type_counts:
            print(f"{item['form_type']}: {item['count']}")
        
        # Get failed documents by error type
        print("\n===== Failed Documents by Error Type =====")
        error_groups = get_failed_by_error_type(driver)
        for i, group in enumerate(error_groups[:10]):  # Show top 10 error types
            print(f"\n{i+1}. Error: {format_error_message(group['error_message'])}")
            print(f"   Count: {group['count']}")
            print(f"   Form Types: {', '.join(group['form_types'])}")
        
        if len(error_groups) > 10:
            print(f"\n... and {len(error_groups) - 10} more error types")
        
        # Get detailed list of recent failures
        print("\n===== Recent Failed Documents (Latest 20) =====")
        failed_docs = get_failed_xbrl_details(driver, limit=20)
        
        if failed_docs:
            # Create a simple table
            print(f"\n{'Accession':<22} {'CIK':<12} {'Form':<8} {'Filed':<12} {'Error'}")
            print("-" * 100)
            for doc in failed_docs:
                accession = doc['accession'] or 'N/A'
                cik = doc['cik'] or 'N/A'
                form_type = doc['form_type'] or 'N/A'
                filed_at = doc['filed_at'] or 'N/A'
                if filed_at != 'N/A' and len(filed_at) >= 10:
                    filed_at = filed_at[:10]  # Just the date part
                error = format_error_message(doc['error'], 40)
                
                print(f"{accession:<22} {cik:<12} {form_type:<8} {filed_at:<12} {error}")
        
        # Option to export all failed documents
        export = input("\n\nExport all failed documents to CSV? (y/n): ").strip().lower()
        if export == 'y':
            all_failed = get_failed_xbrl_details(driver)
            if all_failed:
                df = pd.DataFrame(all_failed)
                filename = f"failed_xbrl_documents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(filename, index=False)
                print(f"\n✅ Exported {len(all_failed)} failed documents to {filename}")
            
    finally:
        # Close the Neo4j connection
        driver.close()
        logger.info("Failed XBRL Documents Report completed")

if __name__ == "__main__":
    main()