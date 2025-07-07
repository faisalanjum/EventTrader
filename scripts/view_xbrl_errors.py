#!/usr/bin/env python
"""
View XBRL Errors
----------------
Simple script to view XBRL processing errors from failed reports
"""

import os
import sys
import logging
from neo4j import GraphDatabase
from pathlib import Path
from dotenv import load_dotenv
import warnings
from collections import defaultdict

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

def main():
    """Main function to view XBRL errors"""
    neo4j_driver = connect_to_neo4j()
    
    try:
        with neo4j_driver.session() as session:
            # Query all failed XBRL reports
            result = session.run("""
                MATCH (r:Report {xbrl_status: 'FAILED'})
                WHERE r.xbrl_error IS NOT NULL
                RETURN r.accessionNo AS accession,
                       r.cik AS cik,
                       r.formType AS form_type,
                       r.primaryDocumentUrl AS url,
                       r.xbrl_error AS error
                ORDER BY r.accessionNo DESC
            """)
            
            errors = list(result)
            
            if not errors:
                print("\n✅ No XBRL errors found!")
                return
            
            # Group errors by type
            error_groups = defaultdict(list)
            
            for record in errors:
                error_msg = record['error']
                
                # Simple error categorization
                if "HTTP Error 403" in error_msg:
                    key = "HTTP 403 Forbidden"
                elif "HTTP Error 404" in error_msg:
                    key = "HTTP 404 Not Found"
                elif "HTTP Error 500" in error_msg:
                    key = "HTTP 500 Server Error"
                elif "Connection" in error_msg or "Timeout" in error_msg:
                    key = "Connection/Timeout"
                elif "Memory" in error_msg or "memory" in error_msg:
                    key = "Memory Error"
                elif "XML" in error_msg or "parse" in error_msg:
                    key = "XML Parse Error"
                else:
                    # First 60 chars of error
                    key = error_msg[:60] + "..." if len(error_msg) > 60 else error_msg
                
                error_groups[key].append(record)
            
            # Display summary
            print(f"\n===== XBRL Error Summary =====")
            print(f"Total Failed Reports: {len(errors)}")
            print(f"\nError Types:")
            
            for error_type, records in sorted(error_groups.items(), key=lambda x: len(x[1]), reverse=True):
                print(f"\n{error_type}: {len(records)} occurrences")
                print("-" * 80)
                
                # Show first 3 examples
                for i, rec in enumerate(records[:3]):
                    print(f"\n  Example {i+1}:")
                    print(f"  Accession: {rec['accession']}")
                    print(f"  CIK: {rec['cik']}")
                    print(f"  Form: {rec['form_type']}")
                    print(f"  URL: {rec['url']}")
                    if len(rec['error']) > 200:
                        print(f"  Error: {rec['error'][:200]}...")
                    else:
                        print(f"  Error: {rec['error']}")
                
                if len(records) > 3:
                    print(f"\n  ... and {len(records) - 3} more")
                    
    finally:
        neo4j_driver.close()

if __name__ == "__main__":
    main()