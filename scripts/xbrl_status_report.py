#!/usr/bin/env python3
"""
XBRL Status Report
-----------------
Script to query Neo4j for all Report nodes and aggregate their xbrl_status values
"""

import os
import sys
import logging
from collections import Counter, defaultdict
import pandas as pd
from neo4j import GraphDatabase
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)  # Ensures Kubernetes env values take priority

# Neo4j connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
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

def get_xbrl_status_stats(driver):
    """Query Neo4j and get statistics on xbrl_status values"""
    query = """
    MATCH (r:Report)
    RETURN r.xbrl_status AS status, count(r) AS count
    ORDER BY count DESC
    """
    
    with driver.session() as session:
        try:
            result = session.run(query)
            stats = [(record["status"], record["count"]) for record in result]
            return stats
        except Exception as e:
            logger.error(f"Error querying Neo4j: {e}")
            return []

def get_detailed_report(driver):
    """Get a more detailed breakdown of xbrl_status by formType"""
    query = """
    MATCH (r:Report)
    RETURN r.formType AS formType, r.xbrl_status AS status, count(r) AS count
    ORDER BY formType, count DESC
    """
    
    with driver.session() as session:
        try:
            result = session.run(query)
            records = [(record["formType"], record["status"], record["count"]) for record in result]
            return records
        except Exception as e:
            logger.error(f"Error querying Neo4j: {e}")
            return []

def main():
    """Main function to run the script"""
    logger.info("Starting XBRL Status Report")
    
    # Connect to Neo4j
    driver = connect_to_neo4j()
    
    try:
        # Get overall statistics
        stats = get_xbrl_status_stats(driver)
        
        # Print summary
        print("\n===== XBRL Status Summary =====")
        total = sum(count for _, count in stats)
        print(f"Total Reports: {total}\n")
        
        for status, count in stats:
            status_display = status if status is not None else "NULL"
            percentage = (count / total) * 100
            print(f"{status_display}: {count} ({percentage:.2f}%)")
        
        # Get detailed breakdown by form type
        detailed = get_detailed_report(driver)
        
        # Organize by form type
        form_type_stats = defaultdict(Counter)
        for form_type, status, count in detailed:
            form_type = form_type if form_type else "UNKNOWN"
            form_type_stats[form_type][status if status is not None else "NULL"] = count
        
        # Print detailed report
        print("\n===== XBRL Status by Form Type =====")
        for form_type, counter in sorted(form_type_stats.items()):
            form_total = sum(counter.values())
            print(f"\n{form_type} (Total: {form_total})")
            for status, count in counter.most_common():
                percentage = (count / form_total) * 100
                print(f"  {status}: {count} ({percentage:.2f}%)")
        
        # Optional: Create a pandas DataFrame for more analysis
        rows = []
        for form_type, counter in form_type_stats.items():
            for status, count in counter.items():
                rows.append({
                    'formType': form_type,
                    'xbrl_status': status,
                    'count': count
                })
        
        if rows:
            df = pd.DataFrame(rows)
            print("\n===== All Form Type/Status Combinations with Counts =====")
            print(df)
            
            # Uncomment to save to CSV
            # df.to_csv('xbrl_status_report.csv', index=False)
            # print("\nSaved full report to xbrl_status_report.csv")
    
    finally:
        # Close the Neo4j connection
        driver.close()
        logger.info("XBRL Status Report completed")

if __name__ == "__main__":
    main() 