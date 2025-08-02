#!/usr/bin/env python3
"""
Create fulltext indexes on existing Neo4j database.
This is a one-time script to add fulltext indexes for content search.

Usage: python scripts/create_fulltext_indexes.py
"""
import logging
import time
from neo4j import GraphDatabase
from eventtrader.keys import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_fulltext_indexes():
    """Create all fulltext indexes for content nodes"""
    
    # Define all fulltext indexes
    fulltext_indexes = [
        # === CORE FILING CONTENT ===
        {
            "name": "extracted_section_content_ft",
            "label": "ExtractedSectionContent",
            "properties": ["content", "section_name"],
            "description": "All 52 section types (MD&A, Risk Factors, 8-K events, etc.)"
        },
        {
            "name": "exhibit_content_ft",
            "label": "ExhibitContent",
            "properties": ["content", "exhibit_number"],
            "description": "Press releases (EX-99.1), contracts (EX-10.x), presentations"
        },
        {
            "name": "filing_text_content_ft",
            "label": "FilingTextContent",
            "properties": ["content", "form_type"],
            "description": "425 proxies, Schedule 13D, 6-K foreign issuer reports"
        },
        {
            "name": "financial_statement_content_ft",
            "label": "FinancialStatementContent",
            "properties": ["value", "statement_type"],
            "description": "JSON financial data (searchable as text)"
        },
        
        # === TRANSCRIPT CONTENT ===
        {
            "name": "full_transcript_ft",
            "label": "FullTranscriptText",
            "properties": ["content"],
            "description": "Complete earnings call transcripts"
        },
        {
            "name": "prepared_remarks_ft",
            "label": "PreparedRemark",
            "properties": ["content"],
            "description": "Management prepared statements"
        },
        {
            "name": "qa_exchange_ft",
            "label": "QAExchange",
            "properties": ["exchanges"],
            "description": "Q&A dialogue text (JSON)"
        },
        {
            "name": "question_answer_ft",
            "label": "QuestionAnswer",
            "properties": ["content"],
            "description": "Structured Q&A sections"
        },
        
        # === NEWS CONTENT ===
        {
            "name": "news_ft",
            "label": "News",
            "properties": ["title", "body", "teaser"],
            "description": "Market news and analysis"
        },
        
        # === XBRL TEXT FACTS ===
        {
            "name": "fact_textblock_ft",
            "label": "Fact",
            "properties": ["value", "qname"],
            "description": "Accounting policies, risk factors in XBRL TextBlock format (filter is_numeric='0' in queries)"
        },
        
        # === ENTITY AND TAXONOMY CONTENT ===
        {
            "name": "company_ft",
            "label": "Company",
            "properties": ["name", "displayLabel"],
            "description": "Company names and display labels (796 companies)"
        },
        {
            "name": "concept_ft",
            "label": "Concept",
            "properties": ["label", "qname"],
            "description": "XBRL accounting concepts (380,857 concepts)"
        },
        {
            "name": "abstract_ft",
            "label": "Abstract",
            "properties": ["label"],
            "description": "XBRL abstract concepts (41,280 abstracts)"
        }
    ]
    
    driver = None
    try:
        # Connect to Neo4j
        logger.info(f"Connecting to Neo4j at {NEO4J_URI}")
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        
        # Verify connection
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            result.single()
            logger.info("Successfully connected to Neo4j")
        
        # Get existing fulltext indexes
        with driver.session() as session:
            existing_indexes = {}
            result = session.run("SHOW FULLTEXT INDEXES")
            for record in result:
                existing_indexes[record["name"]] = record
            logger.info(f"Found {len(existing_indexes)} existing fulltext indexes")
        
        # Create each index
        created_count = 0
        skipped_count = 0
        
        for ft_index in fulltext_indexes:
            index_name = ft_index["name"]
            
            if index_name in existing_indexes:
                logger.info(f"Index '{index_name}' already exists, skipping")
                skipped_count += 1
                continue
            
            # Create the index
            try:
                with driver.session() as session:
                    props_list = ", ".join(f"n.{prop}" for prop in ft_index["properties"])
                    query = f"""
                    CREATE FULLTEXT INDEX {index_name} IF NOT EXISTS
                    FOR (n:{ft_index["label"]})
                    ON EACH [{props_list}]
                    """
                    
                    logger.info(f"Creating index '{index_name}' for {ft_index['label']} - {ft_index['description']}")
                    session.run(query)
                    created_count += 1
                    
                    # Small delay to avoid overwhelming the database
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Failed to create index '{index_name}': {e}")
                raise
        
        # Verify all indexes were created
        with driver.session() as session:
            # Wait a moment for indexes to register
            time.sleep(2)
            
            result = session.run("SHOW FULLTEXT INDEXES")
            final_indexes = {record["name"]: record for record in result}
            
            logger.info(f"\nIndex Creation Summary:")
            logger.info(f"- Created: {created_count} new indexes")
            logger.info(f"- Skipped: {skipped_count} existing indexes")
            logger.info(f"- Total fulltext indexes: {len(final_indexes)}")
            
            # Check index status
            logger.info("\nIndex Status:")
            for ft_index in fulltext_indexes:
                index_name = ft_index["name"]
                if index_name in final_indexes:
                    status = final_indexes[index_name].get("state", "UNKNOWN")
                    logger.info(f"  {index_name}: {status}")
                else:
                    logger.error(f"  {index_name}: NOT FOUND")
        
        logger.info("\n✅ Fulltext index creation completed successfully!")
        
        # Show example queries
        print("\n" + "="*80)
        print("EXAMPLE QUERIES:")
        print("="*80)
        print("""
# Search for cybersecurity in risk factors:
CALL db.index.fulltext.queryNodes('extracted_section_content_ft', 'cybersecurity')
YIELD node, score
WHERE node.section_name = 'RiskFactors'
RETURN node.filing_id, substring(node.content, 0, 500) as excerpt, score
ORDER BY score DESC
LIMIT 10

# Search news for multiple terms:
CALL db.index.fulltext.queryNodes('news_ft', 'earnings revenue guidance')
YIELD node, score
RETURN node.ticker, node.title, node.created, score
ORDER BY score DESC
LIMIT 20

# Search non-numeric XBRL facts:
CALL db.index.fulltext.queryNodes('fact_textblock_ft', 'accounting policy')
YIELD node, score
WHERE node.is_numeric = '0'
RETURN node.qname, substring(node.value, 0, 1000) as text, score
ORDER BY score DESC
LIMIT 10

# Search companies:
CALL db.index.fulltext.queryNodes('company_ft', 'Apple Microsoft')
YIELD node, score
RETURN node.ticker, node.name, node.displayLabel, score
ORDER BY score DESC
LIMIT 10

# Search accounting concepts:
CALL db.index.fulltext.queryNodes('concept_ft', 'revenue recognition')
YIELD node, score
RETURN node.label, node.qname, score
ORDER BY score DESC
LIMIT 20
""")
        
    except Exception as e:
        logger.error(f"Error during fulltext index creation: {e}", exc_info=True)
        raise
    finally:
        if driver:
            driver.close()
            logger.info("Closed Neo4j connection")

if __name__ == "__main__":
    create_fulltext_indexes()