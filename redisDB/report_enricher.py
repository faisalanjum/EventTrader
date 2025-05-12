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


    try:
        redis_env = EventTraderRedis(source=RedisKeys.SOURCE_REPORTS)
        enrich_queue_client = redis_env.live_client  # Only used for reading from ENRICH_QUEUE

        queues = RedisQueues.get_queues(RedisKeys.SOURCE_REPORTS)
        processed_queue = queues['PROCESSED_QUEUE']
        failed_queue = queues['FAILED_QUEUE']
        processed_channel = RedisKeys.get_pubsub_channel(RedisKeys.SOURCE_REPORTS)
        processed_item_ttl = getattr(feature_flags, 'PROCESSED_ITEM_KEY_TTL', DEFAULT_PROCESSED_KEY_TTL)
        report_processor = ReportProcessor(redis_env, delete_raw=True, ttl=processed_item_ttl)

    except Exception as e:
        logger.critical(f"Enrichment worker {current_process().name} failed during initialization: {e}", exc_info=True)
        return

    client = None
    while True:
        try:
            # Use enrich_queue_client just for queue operations
            payload = enrich_queue_client.client.blpop(RedisKeys.ENRICH_QUEUE, timeout=5)
            if not payload:
                continue

            filing = json.loads(payload[1])
            original_prefix_type = filing.pop("_original_prefix_type", None)
            raw_key = filing.pop("_raw_key", None)
            identifier = raw_key.split(":")[-1] if raw_key else None
            
            if not original_prefix_type or not raw_key:
                logger.critical("_original_prefix_type or _raw_key missing for report %s – discarding", filing.get('id'))
                continue


            meta_key = f"tracking:meta:{RedisKeys.SOURCE_REPORTS}:{identifier}"
            client = redis_env.history_client if original_prefix_type == RedisKeys.PREFIX_HIST else redis_env.live_client
            processed_key = RedisKeys.get_key(
                source_type=RedisKeys.SOURCE_REPORTS,
                key_type=RedisKeys.SUFFIX_PROCESSED,
                prefix_type=original_prefix_type,
                identifier=identifier,
            )

            existing_val = client.client.get(processed_key)
            if existing_val:
                try:
                    if json.loads(existing_val.decode('utf-8') if isinstance(existing_val, bytes) else existing_val).get("enriched"):
                        logger.info("Report %s already enriched – skipping", identifier)
                        continue
                except Exception:
                    pass  # fall-through to re-enrich if malformed


            # ---------------- heavy enrichment operations ----------------
            if filing.get("formType") in FORM_TYPES_REQUIRING_SECTIONS and filing.get("primaryDocumentUrl"):
                filing["extracted_sections"] = report_processor._extract_sections(
                    url=filing["primaryDocumentUrl"],
                    form_type=filing["formType"],
                    items=filing.get("items"),
                )
            elif filing.get("primaryDocumentUrl") and filing.get("formType") not in FORM_TYPES_REQUIRING_SECTIONS:
                filing["filing_text_content"] = report_processor._extract_secondary_filing_content(
                    filing["primaryDocumentUrl"]
                )

            if (
                filing.get("filing_text_content") is None
                and filing.get("cik") is None
                and filing.get("is_xml") is True
                and filing.get("linkToTxt")
            ):
                filing["filing_text_content"] = report_processor._extract_secondary_filing_content(
                    filing["linkToTxt"]
                )

            if filing.get("formType") in FORM_TYPES_REQUIRING_XML:
                filing["financial_statements"] = report_processor._get_financial_statements(
                    accession_no=filing.get("accessionNo", identifier),
                    cik=str(filing.get("cik", "")),
                )

            if filing.get("exhibits"):
                filing["exhibit_contents"] = report_processor._process_exhibits(filing["exhibits"])

            filing["enriched"] = True
            ttl = processed_item_ttl or None

            pipe = client.client.pipeline(transaction=True)

            if ttl:
                pipe.set(processed_key, json.dumps(filing), ex=ttl)
            else:
                pipe.set(processed_key, json.dumps(filing))

            pipe.lpush(processed_queue, processed_key)
            pipe.publish(processed_channel, processed_key)

            # lifecycle (atomic with the writes)
            pipe = client.mark_lifecycle_timestamp(meta_key, "finished_enrichment_at", ttl=ttl, external_pipe=pipe) or pipe
            pipe = client.mark_lifecycle_timestamp(meta_key,"processed_at", ttl=ttl, external_pipe=pipe) or pipe
            pipe.execute()
            logger.info("Enriched report %s", identifier)

        except Exception as exc:

            if client is None:
                client = redis_env.live_client  # or redis_env.history_client as a safe default

            logger.error("Enrichment failed for %s: %s", raw_key, exc, exc_info=True)
            pipe = client.client.pipeline(transaction=True)
            pipe.lpush(failed_queue, raw_key)
            pipe = client.mark_lifecycle_timestamp(
                meta_key,"failed_at",reason="enrichment_worker_unhandled_exception_",external_pipe=pipe) or pipe
            pipe.execute()
            time.sleep(1)


if __name__ == "__main__":
    enrich_worker() 