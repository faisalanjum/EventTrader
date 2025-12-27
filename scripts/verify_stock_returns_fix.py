#!/usr/bin/env python3
"""
Verify the status of stock returns on relationships.

This script helps monitor the progress of fixing NULL stock returns by:
1. Counting relationships with NULL vs populated stock returns
2. Showing sample relationships before/after fix
3. Tracking specific test cases like ACCD
"""

import argparse
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neograph.Neo4jConnection import get_manager
from utils.log_config import setup_logging
import logging

log_file = setup_logging(name="verify_returns")
logger = logging.getLogger(__name__)

class ReturnsVerifier:
    def __init__(self):
        self.neo4j_manager = get_manager()
    
    def get_null_returns_count(self):
        """Count relationships with NULL stock returns."""
        
        query = """
        MATCH ()-[r:INFLUENCES|PRIMARY_FILER]->(:Company)
        WHERE r.hourly_stock IS NULL 
           OR r.session_stock IS NULL 
           OR r.daily_stock IS NULL
        RETURN 
            type(r) as rel_type,
            COUNT(r) as null_count
        """
        
        with self.neo4j_manager.driver.session() as session:
            result = session.run(query)
            counts = {}
            for record in result:
                counts[record['rel_type']] = record['null_count']
        
        return counts
    
    def get_populated_returns_count(self):
        """Count relationships with populated stock returns."""
        
        query = """
        MATCH ()-[r:INFLUENCES|PRIMARY_FILER]->(:Company)
        WHERE r.hourly_stock IS NOT NULL 
          AND r.session_stock IS NOT NULL 
          AND r.daily_stock IS NOT NULL
        RETURN 
            type(r) as rel_type,
            COUNT(r) as populated_count
        """
        
        with self.neo4j_manager.driver.session() as session:
            result = session.run(query)
            counts = {}
            for record in result:
                counts[record['rel_type']] = record['populated_count']
        
        return counts
    
    def check_company_status(self, ticker: str):
        """Check detailed status for a specific company."""
        
        query = """
        MATCH (event)-[r:INFLUENCES|PRIMARY_FILER]->(c:Company {ticker: $ticker})
        RETURN 
            labels(event)[0] as event_type,
            type(r) as rel_type,
            event.id as event_id,
            event.created as event_datetime,
            r.hourly_stock as hourly_stock,
            r.session_stock as session_stock,
            r.daily_stock as daily_stock,
            r.created_at as relationship_created,
            CASE 
                WHEN r.hourly_stock IS NULL OR r.session_stock IS NULL OR r.daily_stock IS NULL
                THEN 'NULL_RETURNS'
                ELSE 'POPULATED'
            END as status
        ORDER BY event.created DESC
        """
        
        logger.info(f"\nChecking relationships for company: {ticker}")
        
        with self.neo4j_manager.driver.session() as session:
            result = session.run(query, ticker=ticker)
            
            null_count = 0
            populated_count = 0
            
            print(f"\n{'Event Type':<12} {'Rel Type':<15} {'Event ID':<30} {'Status':<15} {'Returns (H/S/D)'}")
            print("-" * 100)
            
            for record in result:
                status = record['status']
                if status == 'NULL_RETURNS':
                    null_count += 1
                else:
                    populated_count += 1
                
                returns_str = f"{record['hourly_stock'] or 'NULL'}/{record['session_stock'] or 'NULL'}/{record['daily_stock'] or 'NULL'}"
                
                print(f"{record['event_type']:<12} {record['rel_type']:<15} {record['event_id']:<30} {status:<15} {returns_str}")
        
        print(f"\nSummary for {ticker}:")
        print(f"  Relationships with NULL returns: {null_count}")
        print(f"  Relationships with populated returns: {populated_count}")
        print(f"  Total relationships: {null_count + populated_count}")
    
    def show_sample_events(self, limit: int = 5):
        """Show sample events with NULL returns."""
        
        query = """
        MATCH (event)-[r:INFLUENCES|PRIMARY_FILER]->(c:Company)
        WHERE r.hourly_stock IS NULL 
           OR r.session_stock IS NULL 
           OR r.daily_stock IS NULL
        RETURN 
            event.id as event_id,
            labels(event)[0] as event_type,
            type(r) as rel_type,
            c.ticker as ticker,
            event.created as event_datetime,
            CASE 
                WHEN event:News THEN event.title
                WHEN event:Transcript THEN event.company_name + ' Earnings Call'
                WHEN event:Report THEN event.formType + ': ' + coalesce(event.description, '')
            END as description
        ORDER BY event.created DESC
        LIMIT $limit
        """
        
        logger.info(f"\nSample events with NULL returns (limit: {limit}):")
        
        with self.neo4j_manager.driver.session() as session:
            result = session.run(query, limit=limit)
            
            print(f"\n{'Event Type':<12} {'Ticker':<8} {'Event ID':<30} {'Description'}")
            print("-" * 100)
            
            for record in result:
                desc = record['description'][:50] + '...' if len(record['description']) > 50 else record['description']
                print(f"{record['event_type']:<12} {record['ticker']:<8} {record['event_id']:<30} {desc}")
    
    def run(self, company_ticker: str = None, show_samples: bool = False):
        """Main execution method."""
        
        logger.info("Stock Returns Verification Report")
        logger.info("=" * 50)
        
        # Get overall counts
        null_counts = self.get_null_returns_count()
        populated_counts = self.get_populated_returns_count()
        
        logger.info("\nRelationships with NULL stock returns:")
        total_null = 0
        for rel_type, count in null_counts.items():
            logger.info(f"  {rel_type}: {count:,}")
            total_null += count
        logger.info(f"  TOTAL: {total_null:,}")
        
        logger.info("\nRelationships with POPULATED stock returns:")
        total_populated = 0
        for rel_type, count in populated_counts.items():
            logger.info(f"  {rel_type}: {count:,}")
            total_populated += count
        logger.info(f"  TOTAL: {total_populated:,}")
        
        # Calculate percentage fixed
        total_relationships = total_null + total_populated
        if total_relationships > 0:
            percent_fixed = (total_populated / total_relationships) * 100
            logger.info(f"\nProgress: {percent_fixed:.1f}% of relationships have stock returns")
        
        # Show samples if requested
        if show_samples:
            self.show_sample_events()
        
        # Check specific company if provided
        if company_ticker:
            self.check_company_status(company_ticker)


def main():
    parser = argparse.ArgumentParser(description='Verify stock returns fix progress')
    parser.add_argument('--company', help='Check status for specific company ticker (e.g., ACCD)')
    parser.add_argument('--samples', action='store_true', help='Show sample events with NULL returns')
    
    args = parser.parse_args()
    
    verifier = ReturnsVerifier()
    verifier.run(company_ticker=args.company, show_samples=args.samples)


if __name__ == "__main__":
    main()