#!/usr/bin/env python
"""
Complete XBRL Failure Analysis
------------------------------
Comprehensive analysis of XBRL processing failures focusing on FAILED status
"""

import os
import sys
import logging
from neo4j import GraphDatabase
from pathlib import Path
from dotenv import load_dotenv
import warnings
from collections import defaultdict
import json

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
    """Main analysis function"""
    neo4j_driver = connect_to_neo4j()
    
    try:
        with neo4j_driver.session() as session:
            print("\n" + "="*80)
            print("XBRL PROCESSING FAILURE ANALYSIS (FAILED STATUS ONLY)")
            print("="*80)
            
            # 1. Overview of XBRL processing status
            status_overview = session.run("""
                MATCH (r:Report)
                WITH count(r) as total_reports,
                     count(CASE WHEN r.xbrl_status IS NOT NULL THEN 1 END) as with_status
                MATCH (r2:Report)
                WHERE r2.xbrl_status IS NOT NULL
                RETURN total_reports, 
                       with_status,
                       r2.xbrl_status as status, 
                       count(r2) as count
                ORDER BY count DESC
            """)
            
            results = list(status_overview)
            total_reports = results[0]['total_reports'] if results else 0
            with_status = results[0]['with_status'] if results else 0
            
            print(f"\n📊 XBRL PROCESSING OVERVIEW:")
            print(f"  Total Reports: {total_reports:,}")
            print(f"  Reports with XBRL Status: {with_status:,}")
            print(f"\n  Status Distribution:")
            
            total_processed = 0
            for record in results:
                status = record['status']
                count = record['count']
                percentage = (count / with_status * 100) if with_status > 0 else 0
                print(f"    {status}: {count:,} ({percentage:.1f}%)")
                total_processed += count
            
            # 2. Failed reports analysis
            failed_analysis = session.run("""
                MATCH (r:Report {xbrl_status: 'FAILED'})
                RETURN count(r) as total_failed,
                       count(CASE WHEN r.xbrl_error IS NOT NULL THEN 1 END) as with_error,
                       count(CASE WHEN r.xbrl_error IS NULL THEN 1 END) as without_error,
                       count(CASE WHEN r.cik IS NULL THEN 1 END) as missing_cik
            """).single()
            
            print(f"\n❌ FAILED REPORTS ANALYSIS:")
            print(f"  Total Failed: {failed_analysis['total_failed']:,}")
            print(f"  With Error Message: {failed_analysis['with_error']:,}")
            print(f"  Without Error Message: {failed_analysis['without_error']:,}")
            print(f"  Missing CIK: {failed_analysis['missing_cik']:,}")
            
            # 3. Error categorization
            error_categories = session.run("""
                MATCH (r:Report)
                WHERE r.xbrl_status = 'FAILED' AND r.xbrl_error IS NOT NULL
                WITH r,
                     CASE 
                         WHEN r.xbrl_error = 'Missing CIK - cannot process XBRL' THEN 'Missing CIK'
                         WHEN r.xbrl_error CONTAINS 'No report found' THEN 'Report Not Found'
                         WHEN r.xbrl_error CONTAINS 'DeadlockDetected' THEN 'Neo4j Deadlock'
                         WHEN r.xbrl_error CONTAINS 'HTTP Error' THEN 'HTTP Error'
                         WHEN r.xbrl_error CONTAINS 'Connection' OR r.xbrl_error CONTAINS 'Timeout' THEN 'Connection/Timeout'
                         WHEN r.xbrl_error CONTAINS 'Memory' OR r.xbrl_error CONTAINS 'memory' THEN 'Memory Error'
                         WHEN r.xbrl_error CONTAINS 'XML' OR r.xbrl_error CONTAINS 'parse' THEN 'XML Parse Error'
                         ELSE 'Other'
                     END as error_category
                RETURN error_category, 
                       count(r) as count,
                       collect(DISTINCT r.formType)[0..5] as sample_forms
                ORDER BY count DESC
            """)
            
            print(f"\n🔍 ERROR CATEGORIES:")
            error_data = list(error_categories)
            for record in error_data:
                category = record['error_category']
                count = record['count']
                forms = ', '.join(record['sample_forms'])
                print(f"  {category}: {count} errors")
                print(f"    Form types: {forms}")
            
            # 4. Missing CIK deep dive
            missing_cik_analysis = session.run("""
                MATCH (r:Report)
                WHERE r.xbrl_status = 'FAILED' 
                  AND r.xbrl_error = 'Missing CIK - cannot process XBRL'
                  AND r.cik IS NULL
                WITH r
                RETURN count(r) as total_missing_cik,
                       count(CASE WHEN r.entities IS NOT NULL THEN 1 END) as has_entities_json,
                       count(CASE WHEN EXISTS((r)-[:FILED_BY]->()) THEN 1 END) as has_entity_relation
            """).single()
            
            print(f"\n🔴 MISSING CIK DETAILED ANALYSIS:")
            print(f"  Total with Missing CIK error: {missing_cik_analysis['total_missing_cik']}")
            print(f"  Have entities JSON data: {missing_cik_analysis['has_entities_json']}")
            print(f"  Have FILED_BY relationship: {missing_cik_analysis['has_entity_relation']}")
            
            # Sample of recoverable CIKs
            recoverable_sample = session.run("""
                MATCH (r:Report)
                WHERE r.xbrl_status = 'FAILED' 
                  AND r.xbrl_error = 'Missing CIK - cannot process XBRL'
                  AND r.cik IS NULL
                  AND r.entities IS NOT NULL
                RETURN r.accessionNo as accession,
                       r.formType as form_type,
                       r.entities as entities_json
                LIMIT 3
            """)
            
            print(f"\n  Sample of Recoverable Reports:")
            for i, record in enumerate(recoverable_sample, 1):
                print(f"\n  Example {i}:")
                print(f"    Accession: {record['accession']}")
                print(f"    Form Type: {record['form_type']}")
                try:
                    entities = json.loads(record['entities_json'])
                    if entities:
                        # Usually the first entity is the primary filer
                        primary_cik = entities[0].get('cik', 'Not found')
                        primary_name = entities[0].get('companyName', 'Unknown')
                        print(f"    Recoverable CIK: {primary_cik}")
                        print(f"    Company: {primary_name}")
                        print(f"    Total Entities in JSON: {len(entities)}")
                except:
                    print(f"    Error parsing entities JSON")
            
            # 5. Deadlock analysis
            deadlock_analysis = session.run("""
                MATCH (r:Report)
                WHERE r.xbrl_status = 'FAILED' 
                  AND r.xbrl_error CONTAINS 'DeadlockDetected'
                RETURN count(r) as deadlock_count,
                       collect(DISTINCT r.formType) as form_types
            """).single()
            
            print(f"\n🔒 DEADLOCK ANALYSIS:")
            print(f"  Total Deadlock Failures: {deadlock_analysis['deadlock_count']}")
            print(f"  Affected Form Types: {', '.join(deadlock_analysis['form_types'])}")
            
            # 6. Report not found analysis
            not_found = session.run("""
                MATCH (r:Report)
                WHERE r.xbrl_status = 'FAILED' 
                  AND r.xbrl_error CONTAINS 'No report found'
                RETURN r.accessionNo as accession,
                       r.xbrl_error as error
                ORDER BY r.accessionNo
            """)
            
            not_found_list = list(not_found)
            if not_found_list:
                print(f"\n📄 REPORT NOT FOUND ERRORS ({len(not_found_list)} total):")
                for record in not_found_list:
                    print(f"  {record['accession']}: {record['error']}")
            
            # 7. Other processing states
            other_states = session.run("""
                MATCH (r:Report)
                WHERE r.xbrl_status IN ['QUEUED', 'PROCESSING']
                RETURN r.xbrl_status as status,
                       count(r) as count,
                       count(CASE WHEN r.cik IS NULL THEN 1 END) as missing_cik
            """)
            
            print(f"\n⏳ OTHER PROCESSING STATES:")
            for record in other_states:
                print(f"  {record['status']}: {record['count']:,} reports", end="")
                if record['missing_cik'] > 0:
                    print(f" (⚠️ {record['missing_cik']} missing CIK)")
                else:
                    print()
            
            # 8. Recommendations
            print(f"\n💡 RECOMMENDATIONS:")
            
            print(f"\n  1. FIX MISSING CIK ({missing_cik_analysis['total_missing_cik']} reports):")
            print(f"     • {missing_cik_analysis['has_entities_json']} reports have CIK in entities JSON")
            print(f"     • Extract CIK from entities[0]['cik'] and update Report nodes")
            print(f"     • Script: python scripts/fix_missing_cik.py")
            print(f"     • After fix: Reset xbrl_status to NULL to reprocess")
            
            print(f"\n  2. HANDLE DEADLOCKS ({deadlock_analysis['deadlock_count']} failures):")
            print(f"     • These are transient errors from concurrent processing")
            print(f"     • Implement retry with exponential backoff in worker")
            print(f"     • Consider reducing batch size or adding delays")
            print(f"     • Reset these to NULL status for retry")
            
            if not_found_list:
                print(f"\n  3. INVESTIGATE MISSING REPORTS ({len(not_found_list)} reports):")
                print(f"     • These accession numbers don't exist in database")
                print(f"     • Check if report ingestion failed")
                print(f"     • May need to re-ingest these reports")
            
            # 9. Summary statistics
            total_failed = failed_analysis['total_failed']
            recoverable = missing_cik_analysis['has_entities_json'] + deadlock_analysis['deadlock_count']
            
            print(f"\n📊 RECOVERY POTENTIAL:")
            print(f"  Total Failed: {total_failed:,}")
            print(f"  Potentially Recoverable: {recoverable:,} ({recoverable/total_failed*100:.1f}%)")
            print(f"    - Missing CIK (fixable): {missing_cik_analysis['has_entities_json']:,}")
            print(f"    - Deadlocks (retryable): {deadlock_analysis['deadlock_count']:,}")
            print(f"  Needs Investigation: {len(not_found_list):,}")
            
    finally:
        neo4j_driver.close()

if __name__ == "__main__":
    main()