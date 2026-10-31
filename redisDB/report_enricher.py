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
import hashlib
import traceback
from multiprocessing import current_process
import logging
import redis
from redis.backoff import NoBackoff
from redis.retry import Retry

# Add parent directory to path to import log_config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.log_config import setup_logging

from redisDB.redisClasses import EventTraderRedis
from redisDB.redis_constants import RedisKeys, RedisQueues
from redisDB.ReportProcessor import ReportProcessor
from config.feature_flags import FORM_TYPES_REQUIRING_SECTIONS, FORM_TYPES_REQUIRING_XML
from config import feature_flags

DEFAULT_PROCESSED_KEY_TTL = 2 * 24 * 3600  # 2 days
PREPARED_EXTRACTION_CONFIG = os.environ.get('PREPARED_EXTRACTION_CONFIG')  # explicit adapter config (JSON path); unset = old path only
if PREPARED_EXTRACTION_CONFIG:
    from prepared_filing import pointer, prepared_done  # stdlib-only module; the adapter itself runs as an isolated pinned child

# Reliable claim (only with PREPARED_EXTRACTION_CONFIG): the queue holds the ONLY copy of a payload (the producer deletes raw),
# so the worker moves it to a processing list instead of popping it, and removes it only in the same transaction as its result.
# ponytail: one worker owns the processing list (Recreate deployment, one replica); several workers would need per-owner lists.
ENRICH_PROCESSING = f"{RedisKeys.ENRICH_QUEUE}:processing"  # claimed, not yet finished
ENRICH_DELIVERIES = f"{RedisKeys.ENRICH_QUEUE}:deliveries"  # sha256(payload) -> deliveries ended by a killed worker
ENRICH_DEAD = f"{RedisKeys.ENRICH_QUEUE}:dead"  # terminal failures with the full original payload
UNKNOWN_OUTCOME = (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError)  # an unanswered command may have run
MAX_DELIVERIES = 3


def _text(item):
    return item.decode("utf-8") if isinstance(item, bytes) else item  # production clients use decode_responses=True


def _sha(item):
    return hashlib.sha256(_text(item).encode("utf-8")).hexdigest()


def _ack(pipe, item):
    """Finish a claimed payload inside the caller's transaction (no-op on the old path)."""
    if item is not None:
        pipe.lrem(ENRICH_PROCESSING, 1, item)
        pipe.hdel(ENRICH_DELIVERIES, _sha(item))
    return pipe


def _keep(pipe, key, item, reason):
    """Keep the exact original payload with the reason."""
    pipe.rpush(key, json.dumps({"item": _text(item), "reason": reason[:500], "at": time.time()}))
    return pipe


def _dead(pipe, item, reason):
    return _ack(_keep(pipe, ENRICH_DEAD, item, reason), item)


def reclaim(r):
    """Startup, single owner: put payloads held by a killed worker back at the queue head, oldest first; retire one after MAX_DELIVERIES."""
    for item in reversed(r.lrange(ENRICH_PROCESSING, 0, -1)):
        pipe = r.pipeline(transaction=True)
        if r.hincrby(ENRICH_DELIVERIES, _sha(item), 1) >= MAX_DELIVERIES:
            _dead(pipe, item, f"worker killed during {MAX_DELIVERIES} deliveries")
        else:
            pipe.lrem(ENRICH_PROCESSING, 1, item)
            pipe.lpush(RedisKeys.ENRICH_QUEUE, item)
        pipe.execute()

# Setup centralized logging with "enricher" prefix
setup_logging(name="enricher")
logger = logging.getLogger(f"report_enricher_{current_process().name}")

def enrich_worker():
    """Entry-point for each spawned enrichment process"""

    logger.info("Enrichment worker starting (XBRL generation deferred to Neo4jProcessor)")


    try:
        redis_env = EventTraderRedis(source=RedisKeys.SOURCE_REPORTS, clear_on_init=False)  # the worker never owns the producer's raw items: never wipe them on (re)start or rollback
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

    if PREPARED_EXTRACTION_CONFIG:
        for c in (redis_env.live_client.client, redis_env.history_client.client):
            c.set_retry(Retry(NoBackoff(), 0))  # never resend a command whose reply was lost: it may have run (a 2nd claim, a 2nd publication)
        reclaim(enrich_queue_client.client)

    client = None
    while True:
        item = raw_key = meta_key = None  # per payload: an error path never reuses the previous payload's keys
        try:
            # Use enrich_queue_client just for queue operations
            if PREPARED_EXTRACTION_CONFIG:
                item = enrich_queue_client.client.blmove(RedisKeys.ENRICH_QUEUE, ENRICH_PROCESSING, 5, "LEFT", "RIGHT")
                payload = (RedisKeys.ENRICH_QUEUE, item) if item is not None else None  # an empty payload is still a claimed item
            else:
                payload = enrich_queue_client.client.blpop(RedisKeys.ENRICH_QUEUE, timeout=5)
            if not payload:
                continue

            filing = json.loads(payload[1])
            original_prefix_type = filing.pop("_original_prefix_type", None)
            raw_key = filing.pop("_raw_key", None)
            identifier = raw_key.split(":")[-1] if raw_key else None
            
            if not original_prefix_type or not raw_key:
                logger.critical("_original_prefix_type or _raw_key missing for report %s – discarding", filing.get('id'))
                if item is not None:
                    _dead(enrich_queue_client.client.pipeline(transaction=True), item, "_original_prefix_type or _raw_key missing").execute()
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
                    existing = json.loads(existing_val.decode('utf-8') if isinstance(existing_val, bytes) else existing_val)
                    if existing.get("enriched") and (not PREPARED_EXTRACTION_CONFIG or prepared_done(existing)):  # a missing/failed prepared product is not done
                        logger.info("Report %s already enriched – skipping", identifier)
                        if item is not None:
                            _ack(client.client.pipeline(transaction=True), item).execute()
                        continue
                except UNKNOWN_OUTCOME:
                    raise  # the skip's ack may have run: never fall through to a second publication
                except Exception:
                    pass  # fall-through to re-enrich if malformed


            if PREPARED_EXTRACTION_CONFIG:  # first, on arrival: legacy work below cannot delay or prevent it; enriched=True never means extraction verified
                filing["prepared_extraction"] = pointer(filing, PREPARED_EXTRACTION_CONFIG)  # a receipt locator; never raises

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
            if item is not None and not prepared_done(filing):  # failed prepared extraction (e.g. no package): keep the full input; legacy still publishes
                p = filing.get("prepared_extraction") or {}
                _keep(pipe, ENRICH_DEAD, item, f"prepared_extraction {p.get('status')} (legacy result published): " + "; ".join(p.get("reasons") or []))
            _ack(pipe, item)  # same transaction: published and finished together
            pipe.execute()
            logger.info("Enriched report %s", identifier)

        except Exception as exc:
            if PREPARED_EXTRACTION_CONFIG and isinstance(exc, UNKNOWN_OUTCOME):
                raise  # outcome unknown: stop; a claimed payload stays in processing and the restart's reclaim decides

            if client is None:
                client = redis_env.live_client  # or redis_env.history_client as a safe default

            logger.error("Enrichment failed for %s: %s", raw_key, exc, exc_info=True)
            pipe = client.client.pipeline(transaction=True)
            if raw_key:
                pipe.lpush(failed_queue, raw_key)
            if meta_key:
                pipe = client.mark_lifecycle_timestamp(
                    meta_key,"failed_at",reason="enrichment_worker_unhandled_exception_",external_pipe=pipe) or pipe
            if item is not None:
                _dead(pipe, item, f"{type(exc).__name__}: {exc}")
            pipe.execute()
            time.sleep(1)


if __name__ == "__main__":
    enrich_worker() 