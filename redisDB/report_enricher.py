#!/usr/bin/env python3
"""
Report Enrichment Worker  (moved into redisDB package).
Handles heavy-weight tasks (section extraction, exhibit download, XBRL pre-parse)
so that ReportProcessor itself stays fast.

Spawned by DataManagerCentral.ReportsManager when
feature_flags.ENABLE_REPORT_ENRICHER is True.
"""

import os
import sys
import json
import time
import traceback
from multiprocessing import current_process
import logging

from redisDB.redisClasses import EventTraderRedis
from redisDB.redis_constants import RedisKeys, RedisQueues
from redisDB.ReportProcessor import ReportProcessor
from config.feature_flags import FORM_TYPES_REQUIRING_SECTIONS, FORM_TYPES_REQUIRING_XML
from config import feature_flags

DEFAULT_PROCESSED_KEY_TTL = 2 * 24 * 3600  # 2 days

logger = logging.getLogger(f"report_enricher_{current_process().name}")

def enrich_worker():
    """Entry-point for each spawned enrichment process"""
    if not logging.root.handlers:
        worker_log_level_str = getattr(feature_flags, "GLOBAL_LOG_LEVEL", "INFO").upper()
        worker_log_level_int = getattr(logging, worker_log_level_str, logging.INFO)
        logging.basicConfig(
            level=worker_log_level_int, 
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger.info(f"Worker process {current_process().name} configured basic logging.")

    logger.info("Enrichment worker starting (XBRL generation deferred to Neo4jProcessor)")

    redis_env = EventTraderRedis(source=RedisKeys.SOURCE_REPORTS)
    client = redis_env.live_client

    queues = RedisQueues.get_queues(RedisKeys.SOURCE_REPORTS)
    processed_queue = queues['PROCESSED_QUEUE']
    processed_channel = RedisKeys.get_pubsub_channel(RedisKeys.SOURCE_REPORTS)

    processed_item_ttl = getattr(feature_flags, 'PROCESSED_ITEM_KEY_TTL', DEFAULT_PROCESSED_KEY_TTL)

    report_processor = ReportProcessor(redis_env, delete_raw=False, ttl=processed_item_ttl)

    while True:
        try:
            payload = client.client.blpop(RedisKeys.ENRICH_QUEUE, timeout=5)
            if not payload:
                continue

            filing = json.loads(payload[1])
            original_prefix_type = filing.pop('_original_prefix_type', None)
            if not original_prefix_type:
                logger.critical("_original_prefix_type missing for report %s – discarding", filing.get('id'))
                continue

            identifier = filing.get('id')
            processed_key = RedisKeys.get_key(
                source_type=RedisKeys.SOURCE_REPORTS,
                key_type=RedisKeys.SUFFIX_PROCESSED,
                prefix_type=original_prefix_type,
                identifier=identifier,
            )

            # Skip if already enriched.
            existing_val = client.client.get(processed_key)
            if existing_val:
                json_str = existing_val.decode('utf-8') if isinstance(existing_val, bytes) else existing_val
                try:
                    if json.loads(json_str).get('enriched') is True:
                        logger.info("Report %s already enriched – skipping", identifier)
                        continue
                except Exception:
                    pass  # fall-through to re-enrich if malformed

            # --- Heavy processing ---
            if (
                filing.get('formType') in FORM_TYPES_REQUIRING_SECTIONS
                and filing.get('primaryDocumentUrl')
            ):
                filing['extracted_sections'] = report_processor._extract_sections(
                    url=filing['primaryDocumentUrl'],
                    form_type=filing['formType'],
                    items=filing.get('items'),
                )
            elif filing.get('primaryDocumentUrl') and filing.get('formType') not in FORM_TYPES_REQUIRING_SECTIONS:
                filing['filing_text_content'] = report_processor._extract_secondary_filing_content(
                    filing['primaryDocumentUrl']
                )

            if (
                filing.get('filing_text_content') is None
                and filing.get('cik') is None
                and filing.get('is_xml') is True
                and filing.get('linkToTxt')
            ):
                filing['filing_text_content'] = report_processor._extract_secondary_filing_content(
                    filing['linkToTxt']
                )

            if filing.get('formType') in FORM_TYPES_REQUIRING_XML:
                filing['financial_statements'] = report_processor._get_financial_statements(
                    accession_no=filing.get('accessionNo', identifier),
                    cik=str(filing.get('cik', '')),
                )

            if filing.get('exhibits'):
                filing['exhibit_contents'] = report_processor._process_exhibits(filing['exhibits'])

            filing['enriched'] = True
            meta = report_processor._add_metadata(filing)
            if meta:
                filing['metadata'] = meta

            if processed_item_ttl > 0:
                client.client.set(processed_key, json.dumps(filing), ex=processed_item_ttl)
            else:
                client.client.set(processed_key, json.dumps(filing))
            client.client.lpush(processed_queue, processed_key)
            client.client.publish(processed_channel, processed_key)
            logger.info("Enriched report %s", identifier)

        except Exception as exc:
            logger.error(f"Error processing enrichment: {exc}", exc_info=True)
            time.sleep(1)


if __name__ == "__main__":
    enrich_worker() 