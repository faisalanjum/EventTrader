#!/usr/bin/env python3
"""
Worker process to handle report enrichment tasks (textual and pre-parsed financials).
XBRL graph processing is deferred to Neo4jProcessor.
"""

import os
import sys
import json
import time
import traceback
from multiprocessing import current_process

# Path handling to import from project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redisDB.redisClasses import EventTraderRedis, RedisClient
from redisDB.redis_constants import RedisKeys, RedisQueues
from redisDB.ReportProcessor import ReportProcessor
from config.feature_flags import FORM_TYPES_REQUIRING_SECTIONS, FORM_TYPES_REQUIRING_XML
from utils.log_config import get_logger, setup_logging
from config import feature_flags # Ensure feature_flags is imported

# Define at module level or fetch from a central config if it can vary
# This should match the ttl intended for processed items.
# DataSourceManager uses ttl: int = 2 * 24 * 3600 by default.
# Let's make it configurable via feature_flags for consistency.
DEFAULT_PROCESSED_KEY_TTL = 2 * 24 * 3600 

def enrich_worker():
    """Main worker function that processes enrichment tasks"""
    setup_logging()
    logger = get_logger(f"report_enricher_{current_process().name}")
    logger.info(f"Enrichment worker starting (XBRL graph processing deferred to Neo4jProcessor)")
    
    redis_env = EventTraderRedis(source=RedisKeys.SOURCE_REPORTS)
    client = redis_env.live_client
    
    queue_names = RedisQueues.get_queues(RedisKeys.SOURCE_REPORTS)
    processed_queue = queue_names['PROCESSED_QUEUE']
    
    processed_channel = RedisKeys.get_pubsub_channel(RedisKeys.SOURCE_REPORTS)

    # Get the TTL for processed keys, defaulting if not in feature_flags
    # This TTL will be passed to the ReportProcessor instance if needed for any internal logic,
    # and used by the worker for the final SET operation.
    processed_item_ttl = getattr(feature_flags, 'PROCESSED_ITEM_KEY_TTL', DEFAULT_PROCESSED_KEY_TTL)

    # Pass the determined TTL to the ReportProcessor instance
    report_processor = ReportProcessor(redis_env, delete_raw=False, ttl=processed_item_ttl)
    
    while True:
        try:
            payload = client.client.blpop(RedisKeys.ENRICH_QUEUE, timeout=5)
            if not payload:
                continue
                
            filing = json.loads(payload[1])
            original_prefix_type = filing.pop('_original_prefix_type', None)
            # logger.info(f"Processing enrichment for {filing.get('formType')} filing {filing.get('id')}, original prefix: {original_prefix_type}") # Original log

            if not original_prefix_type:
                logger.critical(f"CRITICAL: _original_prefix_type missing for filing {filing.get('id')}. Cannot determine correct namespace. Discarding item. Payload: {payload[1][:500]}")
                # Optionally, push to a new "malformed_enrich_item" queue:
                # try:
                #     client.client.rpush(f"{RedisKeys.SOURCE_REPORTS}:queues:malformed_enrich", payload[1]) # Store original payload
                # except Exception as push_err:
                #     logger.error(f"Could not push to malformed_enrich queue: {push_err}")
                continue # Skip this item
            
            # Now original_prefix_type is guaranteed to be non-None, update log message
            logger.info(f"Processing enrichment for {filing.get('formType')} filing {filing.get('id')}, original prefix: {original_prefix_type}")

            # --- Duplicate Enrichment Guard (Uses original_prefix_type) ---
            identifier = filing.get('id')
            potential_processed_key = RedisKeys.get_key(
                source_type=RedisKeys.SOURCE_REPORTS,
                key_type=RedisKeys.SUFFIX_PROCESSED,
                prefix_type=original_prefix_type, 
                identifier=identifier
            )
            existing_processed_data_bytes = client.client.get(potential_processed_key) # Returns bytes by default
            if existing_processed_data_bytes:
                try:
                    existing_processed_data_json = existing_processed_data_bytes.decode('utf-8') # Decode bytes to string
                    existing_processed_data = json.loads(existing_processed_data_json)
                    if existing_processed_data.get('enriched') == True:
                        logger.info(f"Report {identifier} ({potential_processed_key}) already enriched. Skipping duplicate enrichment.")
                        continue 
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse existing processed data for {identifier} ({potential_processed_key}). Proceeding with enrichment.")
                except UnicodeDecodeError:
                    logger.warning(f"Could not decode existing processed data (UTF-8) for {identifier} ({potential_processed_key}). Proceeding with enrichment.")
            # --- End Duplicate Enrichment Guard ---
            
            # --- TEXTUAL & PRE-PARSED FINANCIALS ENRICHMENT SECTION ---
            
            if filing.get('formType') in FORM_TYPES_REQUIRING_SECTIONS and filing.get('primaryDocumentUrl'):
                logger.info(f"Extracting sections for {filing.get('formType')} filing {filing.get('id')}")
                extracted_sections = report_processor._extract_sections(
                    url=filing.get('primaryDocumentUrl'),
                    form_type=filing.get('formType'),
                    items=filing.get('items')
                )
                if extracted_sections:
                    filing['extracted_sections'] = extracted_sections
                    logger.info(f"Successfully extracted sections for {filing.get('formType')}")
                    
            elif filing.get('primaryDocumentUrl') and filing.get('formType') not in FORM_TYPES_REQUIRING_SECTIONS:
                logger.info(f"Form type {filing.get('formType')} doesn't require sections, extracting document text")
                text_content = report_processor._extract_secondary_filing_content(filing.get('primaryDocumentUrl'))
                if text_content:
                    filing['filing_text_content'] = text_content
                    logger.info(f"Successfully extracted document text from primaryDocumentUrl")
            
            if (filing.get('filing_text_content') is None and 
                filing.get('cik') is None and 
                filing.get('is_xml') is True and 
                filing.get('linkToTxt')):
                logger.info(f"Document text not available, CIK is null with XML filing, attempting extract from text link")
                fallback_content = report_processor._extract_secondary_filing_content(filing.get('linkToTxt'))
                if fallback_content:
                    filing['filing_text_content'] = fallback_content
                    logger.info(f"Successfully extracted document text from linkToTxt (fallback)")
            
            # Pre-parse financial statements if it's an XML form (uses XbrlApi.xbrl_to_json)
            if filing.get('formType') in FORM_TYPES_REQUIRING_XML:
                logger.info(f"Pre-parsing financial statements for {filing.get('id')}")
                financial_statements = report_processor._get_financial_statements(
                    accession_no=filing.get('accessionNo', filing.get('id')),
                    cik=str(filing.get('cik', ''))
                )
                if financial_statements:
                    filing['financial_statements'] = financial_statements
                    logger.info(f"Successfully pre-parsed financial statements")
            
            if filing.get('exhibits'):
                logger.info(f"Found {len(filing.get('exhibits'))} exhibits, attempting to extract content")
                exhibit_contents = report_processor._process_exhibits(filing.get('exhibits'))
                if exhibit_contents:
                    filing['exhibit_contents'] = exhibit_contents
                    logger.info(f"Successfully extracted {len(exhibit_contents)} exhibits")
            
            filing['enriched'] = True # Indicates textual/pre-parsed financial enrichment complete
            
            metadata = report_processor._add_metadata(filing)
            if metadata:
                filing['metadata'] = metadata
            
            processed_key = RedisKeys.get_key(
                source_type=RedisKeys.SOURCE_REPORTS,
                key_type=RedisKeys.SUFFIX_PROCESSED,
                prefix_type=original_prefix_type, # USE THE PRESERVED ORIGINAL PREFIX TYPE
                identifier=filing.get('id')
            )
            
            # Use the fetched/defaulted processed_item_ttl for the final SET operation
            if processed_item_ttl and processed_item_ttl > 0:
                client.client.set(processed_key, json.dumps(filing), ex=processed_item_ttl)
            else:
                client.client.set(processed_key, json.dumps(filing))
                
            client.client.lpush(processed_queue, processed_key)
            client.client.publish(processed_channel, processed_key)
            
            logger.info(f"Successfully enriched (textual/financials) filing {filing.get('id')}")
            
        except Exception as e:
            logger.error(f"Error processing enrichment: {e}")
            traceback.print_exc()
            # Optional: Push to a failed_enrich_queue here if desired for robustness
            # client.client.rpush(f"{RedisKeys.SOURCE_REPORTS}:queues:failed_enrich", json.dumps({"original_filing": filing, "error": str(e), "traceback": traceback.format_exc()}))
            time.sleep(1)
    

if __name__ == "__main__":
    enrich_worker() 