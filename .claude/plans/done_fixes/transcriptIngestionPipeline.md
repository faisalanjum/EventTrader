 Complete Transcript Ingestion Pipeline Deep Dive

  High-Level Architecture Overview

  The transcript pipeline has 6 major stages across 3 systems (EarningsCall API → Redis → Neo4j), with 2 distinct ingestion
  pathways (live and historical).

  EarningsCall API → EarningsCallProcessor → Redis (raw) → BaseProcessor/TranscriptProcessor
  → Redis (processed) → ReturnsProcessor → Redis (withreturns/withoutreturns)
  → Neo4j (PubSub or batch) → Embeddings (OpenAI)

  KEY ARCHITECTURAL DIFFERENCE FROM NEWS INGESTION:
  The transcript pipeline requires an LLM call (GPT-4o) for speaker classification during ingestion
  (classify_speakers() at EarningsCallTranscripts.py:476). Every single transcript hits OpenAI to
  classify speakers as ANALYST/EXECUTIVE/OPERATOR before the data even reaches Redis. A second LLM
  call (GPT-4o-mini) filters filler/greeting QA exchanges during Neo4j insertion (transcript.py:41-68).
  Benzinga news is pure API fetch → store — no LLM in the loop. This makes transcript ingestion
  fundamentally slower, more expensive, and harder to run as an always-on pod processing thousands
  of transcripts automatically. It also creates a hard dependency on OpenAI model availability
  (see GAP-20 in transcript-fix-gaps-validation.md — GPT-4o retirement).

  ---
  STAGE 1: Entry Points & Orchestration

  1A. The Main Entry Point: scripts/run_event_trader.py

  - Parses CLI args: --from-date, --to-date, -historical, -live
  - Sets feature_flags.ENABLE_HISTORICAL_DATA and feature_flags.ENABLE_LIVE_DATA
  - Creates DataManager(date_from, date_to) from config/DataManagerCentral.py

  1B. DataManager Orchestration (config/DataManagerCentral.py:669)

  - DataManager.__init__() calls initialize_sources() then initialize_neo4j()
  - IMPORTANT: ReportsManager is still commented out in production (line 692: # self.sources['reports'] =
  ReportsManager(...)) — news and transcripts are active, reports disabled (BENZINGA_ONLY mode for reports only)
  - TranscriptsManager re-enabled 2026-03-03 (commit fd7bfd4)

  1C. TranscriptsManager (config/DataManagerCentral.py:397-664)

  - Extends DataSourceManager with source_type=RedisKeys.SOURCE_TRANSCRIPTS
  - Creates EventTraderRedis(source='transcripts') which sets up two RedisClient instances:
    - live_client with prefix transcripts:live:
    - history_client with prefix transcripts:hist:
  - Creates EarningsCallProcessor(api_key, redis_client, ttl=2 days)
  - Creates TranscriptProcessor(redis, delete_raw=True, ttl=2 days) (extends BaseProcessor)
  - Creates ReturnsProcessor(redis, polygon_subscription_delay=17min)

  1D. TranscriptsManager.start() launches 3 threads:

  1. Processor thread → TranscriptProcessor.process_all_transcripts() (BaseProcessor queue loop + scheduling)
  2. Returns thread → ReturnsProcessor.process_all_returns() (calculates stock returns)
  3. Historical thread (conditional) → _fetch_historical_data() (date-by-date fetching)

  Plus a scheduling initialization at start: _initialize_transcript_schedule() for live transcripts.

  ---
  STAGE 2: Fetching Transcripts from EarningsCall API

  2A. Historical Fetch (TranscriptsManager._fetch_historical_data, line 510)

  - Iterates day-by-day from start_date to end_date
  - For each day calls earnings_call_client.get_transcripts_for_single_date(current_date)
  - Stores each transcript via store_transcript_in_redis(transcript, is_live=False) → history client
  - Sets batch:{transcripts:from-to}:fetch_complete = "1" when done
  - 1-second delay between dates for rate limiting, 5-second delay after errors

  2B. Live Fetch (TranscriptsManager._initialize_transcript_schedule, line 463)

  - Gets today's earnings calendar via get_earnings_events(today)
  - Filters to companies in the stock universe
  - Schedules each event 30 minutes after conference time in Redis sorted set admin:transcripts:schedule
  - Event key format: canonical DATETIME via get_transcript_key_id() (e.g., AAPL_2025-01-10T16.30)
  - Fixed 2026-03-03 (commit 5f732b8): was LONG format causing 5-min retry loops
  - Publishes notification to admin:transcripts:notifications

  2C. The actual API call chain: get_transcripts_for_single_date (line 92)

  1. Calls earningscall.get_calendar(target_date) → gets all events for that date
  2. Filters to companies in self.company_dict (from load_companies())
  3. For each event where transcript_ready == True, calls get_single_event(company_obj, event)

  2D. get_single_event (line 208) — THE CORE EXTRACTION LOGIC

  This is the most complex function. It builds a single transcript dict:

  result = {
      "symbol": ..., "company_name": ...,
      "fiscal_quarter": ..., "fiscal_year": ...,
      "calendar_quarter": None, "calendar_year": None,
      "conference_datetime": event_date (NY timezone),
      "speakers": {}, "prepared_remarks": [],
      "questions_and_answers": [], "qa_pairs": [],
      "full_transcript": "", "speaker_roles_LLM": {}
  }

  Step-by-step:

  1. Level 3 transcript (company_obj.get_transcript(event, level=3)) — contains speakers with start_times and text
  2. Speaker extraction: Iterates transcript_level3.speakers → builds result["speakers"] dict (name → title)
  3. LLM speaker classification: Calls classify_speakers() → OpenAI Responses API with structured JSON output → classifies each
   speaker as ANALYST, EXECUTIVE, or OPERATOR
    - Model: SPEAKER_CLASSIFICATION_MODEL from feature flags
    - Uses rate limiter (ModelRateLimiter) to respect RPM
  4. Segment creation: Builds (start_time, formatted_text, raw_text) tuples from level 3 speakers
    - Format: "Speaker Name [timestamp]: text"
  5. Level 4 transcript attempt (company_obj.get_transcript(event, level=4)) — has pre-split prepared_remarks and
  questions_and_answers
  6. Q&A boundary detection (3 strategies in priority order):
    - Method 1 (Level 4 available + valid Q&A text): Matches first 80 chars of Q&A text against segments
    - Method 1 fallback (Level 4 Q&A empty or no match): First ANALYST speaker = Q&A start
    - Method 2 (no Level 4): First ANALYST speaker = Q&A start
  7. Splitting: Segments before Q&A boundary → prepared_remarks; after → questions_and_answers
  8. Q&A pair formation: form_qa_pairs() — groups exchanges by analyst question:
    - Each new ANALYST speaker starts a new pair
    - EXECUTIVE speakers get added to current pair's answers
    - OPERATOR speakers are skipped
    - Produces structured pairs with questioner, questioner_title, responders, responder_title, exchanges[]
  9. Calendar quarter mapping: fiscal_to_calendar() using company's fiscal_year_end_month
  10. Full transcript fallback: If prepared_remarks or qa_pairs are empty, fetches level 1 transcript as plain text
  11. Validation: _validate_transcript() validates against UnifiedTranscript Pydantic schema (non-blocking — logs warnings but
  always returns original dict)
  12. Error handler: On exception, attempts level 1 transcript fallback with same structure

  ---
  STAGE 3: Storing in Redis (store_transcript_in_redis, line 730)

  Key construction:
  transcript_id = RedisKeys.get_transcript_key_id(symbol, conference_datetime)
  # → "{SYMBOL}_{YYYY-MM-DDTHH.MM}" e.g. "AAPL_2025-01-10T16.30" (DATETIME format, truncated to minute)

  raw_key = f"{client.prefix}raw:{transcript_id}"
  # Live:  "transcripts:live:raw:AAPL_2025-01-10T16.30"
  # Hist:  "transcripts:hist:raw:AAPL_2025-01-10T16.30"

  meta_key = f"tracking:meta:transcripts:{transcript_id}"

  Atomic Redis pipeline:
  1. SET raw_key → JSON(transcript) (with optional TTL)
  2. LPUSH {source}:queues:raw → raw_key (adds to raw queue)
  3. mark_lifecycle_timestamp(meta_key, "ingested_at") — writes timestamp to hash, adds to tracking:pending:transcripts set
  4. set_lifecycle_data(meta_key, "source_api_timestamp", conference_datetime) — writes source timestamp

  ---
  STAGE 4: BaseProcessor Queue Processing

  4A. TranscriptProcessor.process_all_transcripts (line 32)

  - Starts a scheduling daemon thread for live transcript polling
  - Calls BaseProcessor.process_all_items() (the main queue loop)

  4B. BaseProcessor.process_all_items (line 80)

  - Infinite while self.should_run loop
  - BRPOP from {source}:queues:raw (blocking pop with 1s timeout)
  - Calls _process_item(raw_key) for each item

  4C. BaseProcessor._process_item (line 140) — THE REDIS PROCESSING PIPELINE

  1. Determine client: hist_client if key starts with transcripts:hist:, else live_client
  2. Fetch raw content: client.get(raw_key) → JSON parse
  3. Standardize fields (TranscriptProcessor._standardize_fields, line 336):
    - Adds id = RedisKeys.get_transcript_key_id(symbol, conference_datetime) → DATETIME format (e.g., AAPL_2025-01-10T16.30)
    - Adds quarter_key = "{symbol}_{fiscal_year}_{fiscal_quarter}" (e.g., AAPL_2025_1)
    - Adds created and updated = conference_datetime in ISO format
    - Adds symbols = [symbol]
    - Adds formType = "TRANSCRIPT_Q{quarter}"
  4. Symbol validation: Checks if any symbol in self.allowed_symbols (stock universe)
    - If no valid symbols → marks filtered_at with reason no_valid_symbols, deletes raw, returns
  5. Clean content (TranscriptProcessor._clean_content, line 366): Converts created/updated to Eastern timezone
  6. Filter to valid symbols: Intersection with self.allowed_symbols
  7. Add metadata (BaseProcessor._add_metadata, line 373):
    - Creates EventReturnsManager instance
    - Calls process_event_metadata(event_time, symbols) → generates return timing schedules
    - Produces metadata.event (market session info), metadata.returns_schedule (hourly/session/daily windows),
  metadata.instruments (per-symbol data)
  8. Store processed:
    - Key: transcripts:{live|hist}:processed:{identifier}
    - SET processed_key → JSON(processed_dict) with TTL
    - LPUSH {source}:queues:processed → processed_key
    - PUBLISH transcripts:live:processed → processed_key (PubSub notification)
    - mark_lifecycle_timestamp(meta_key, "processed_at")
    - Delete raw key if delete_raw=True

  4D. Live Transcript Scheduling (TranscriptProcessor._run_transcript_scheduling)

  - Only runs if ENABLE_LIVE_DATA = True
  - Subscribes to admin:transcripts:notifications PubSub channel
  - Polls admin:transcripts:schedule sorted set (Redis ZRANGEBYSCORE)
  - For due items, calls _fetch_and_process_transcript(event_key, now_ts):
    - Checks if already in processed queue (_transcript_exists)
    - Creates new EarningsCallProcessor instance
    - Calls get_transcripts_for_single_date(conf_date) then stores via store_transcript_in_redis(is_live=True)
    - If not found, reschedules with 5-minute retry (TRANSCRIPT_RESCHEDULE_INTERVAL)
    - Max sleep between checks: MAX_TRANSCRIPT_SLEEP_SECONDS

  ---
  STAGE 5: Returns Processing (ReturnsProcessor)

  The ReturnsProcessor runs in its own thread, handling both live and historical items:

  1. Listens to transcripts:live:processed PubSub channel + polls processed queues
  2. For each processed transcript, schedules returns calculation using Polygon API
  3. Calculates hourly, session, and daily returns for stock, sector ETF, industry ETF, and SPY (macro)
  4. Stores enriched transcript in two possible namespaces:
    - transcripts:withreturns:{id} — has all return data
    - transcripts:withoutreturns:{id} — returns couldn't be calculated (market closed, holiday, etc.)
  5. Publishes to PubSub channels: transcripts:withreturns or transcripts:withoutreturns
  6. Adds to pending sorted set transcripts:pending_returns with scheduled timestamp

  ---
  STAGE 6: Neo4j Insertion (Two Pathways)

  6A. PubSub-Driven Path (Real-time, neograph/mixins/pubsub.py)

  The Neo4jProcessor.process_with_pubsub() runs in its own thread:
  - Subscribes to 6 channels: {news|reports|transcripts}:{withreturns|withoutreturns}
  - On receiving a transcript message, calls _process_pubsub_item(channel, item_id, 'transcript') (line 146):
    a. Builds Redis key: transcripts:{withreturns|withoutreturns}:{item_id}
    b. Fetches data from history_client, falls back to live_client
    c. Calls _process_deduplicated_transcript(item_id, transcript_data)
    d. On success: generates QAExchange embeddings immediately via _create_qaexchange_embedding(qa_id)
    e. Finalizes: writes lifecycle timestamp, deletes withreturns key if success

  6B. Batch Path (neograph/mixins/transcript.py:process_transcripts_to_neo4j, line 147)

  Called by process_transcript_data() from Neo4jProcessor.py or on startup:
  1. Scans for keys matching transcripts:withreturns:* and transcripts:withoutreturns:*
  2. Processes in batches of 5 (default batch_size=5)
  3. For each key: extracts namespace, fetches data, calls _process_deduplicated_transcript()
  4. Atomic finalization via _finalize_transcript_batch():
    - Success: marks inserted_into_neo4j_at in meta hash
    - Only deletes withreturns keys (verified by checking meta exists first)
    - Failure: marks failed_at with reason

  6C. The Core Neo4j Write: _process_deduplicated_transcript (line 302)

  Calls _prepare_transcript_data() then _execute_transcript_database_operations():

  _prepare_transcript_data (line 261):
  1. Gets universe data → builds ticker_to_cik mapping
  2. Creates TranscriptNode via _create_transcript_node_from_data()
  3. Extracts symbols from data
  4. Parses timestamps (created, updated)
  5. Calls _prepare_entity_relationship_params() → builds params for Company, Sector, Industry, MarketIndex relationships

  _execute_transcript_database_operations (line 336):
  1. Merge Transcript node via manager.merge_nodes([transcript_node])
    - Neo4j label: Transcript
    - Properties: id, symbol, company_name, conference_datetime, fiscal_quarter, fiscal_year, formType, calendar_quarter,
  calendar_year, created, updated, speakers (JSON string)
  2. HAS_TRANSCRIPT relationship: (Company {cik}) -[:HAS_TRANSCRIPT]-> (Transcript {id})
  3. INFLUENCES relationships (4 types):
    - (Transcript) -[:INFLUENCES {symbol, created_at, hourly_stock, session_stock, daily_stock, ...}]-> (Company {cik})
    - (Transcript) -[:INFLUENCES {hourly_sector, session_sector, daily_sector}]-> (Sector {id})
    - (Transcript) -[:INFLUENCES {hourly_industry, session_industry, daily_industry}]-> (Industry {id})
    - (Transcript) -[:INFLUENCES {hourly_macro, session_macro, daily_macro}]-> (MarketIndex {id: 'SPY'})
  4. Process transcript content via _process_transcript_content()

  6D. _process_transcript_content (line 382) — CONTENT NODE CREATION

  Creates child nodes with a priority waterfall:

  Level 1 — Always created if data exists:
  - PreparedRemarkNode with id {transcript_id}_pr, content = JSON-serialized list of remarks
  - Relationship: (Transcript) -[:HAS_PREPARED_REMARKS]-> (PreparedRemark)

  Level 2 — QAExchange nodes (if qa_pairs exist):
  - Creates vector index: _create_qaexchange_vector_index() (cosine, 3072 dimensions)
  - For each Q&A pair:
    - Flattens exchanges: converts {question: {text, speaker, title}} → {role: "question", text, speaker, title}
    - Substantiality filter: _is_qa_content_substantial() — if combined text < QA_SUBSTANTIAL_WORD_COUNT (15 words), calls
  OpenAI LLM to check if it's just filler/greetings
    - Only substantial pairs get nodes
    - Node id: {transcript_id}_qa__{sequence_number} (e.g., AAPL_2025_1_qa__0)
    - Properties: id, transcript_id, exchanges (JSON string), questioner, questioner_title, responders, responder_title,
  sequence
    - Relationships:
        - (Transcript) -[:HAS_QA_EXCHANGE]-> (QAExchange)
      - (QAExchange) -[:NEXT_EXCHANGE]-> (QAExchange) (linked list between sequential valid exchanges)

  Level 2 Fallback — QuestionAnswerNode (if no qa_pairs but questions_and_answers exists):
  - Single node with id {transcript_id}_qa, content = full Q&A section
  - Relationship: (Transcript) -[:HAS_QA_SECTION]-> (QuestionAnswer)

  Level 3 Fallback — FullTranscriptTextNode (if neither qa_pairs nor Q&A):
  - Single node with id {transcript_id}_full, content = full text (truncated at 1MB)
  - Relationship: (Transcript) -[:HAS_FULL_TEXT]-> (FullTranscriptText)

  ---
  STAGE 7: Embedding Generation

  7A. Real-time (PubSub path, pubsub.py:174)

  After successful transcript processing:
  1. Queries Neo4j for all QAExchange nodes linked to this transcript where embedding IS NULL
  2. For each, calls _create_qaexchange_embedding(qa_id):
    - Fetches exchanges JSON from Neo4j
    - Extracts text from question/answer roles
    - Truncates to model token limit
    - Checks ChromaDB cache first (content hash lookup)
    - If not cached: calls OpenAI embeddings API (OPENAI_EMBEDDING_MODEL, 3072 dimensions)
    - Stores embedding on QAExchange.embedding property in Neo4j
    - Caches in ChromaDB for future reuse

  7B. Batch (post-processing, embedding.py:573)

  Called by process_transcript_data() after batch Neo4j insertion:
  1. Queries all QAExchange nodes where embedding IS NULL
  2. For each: parses exchanges JSON → extracts text → truncates → writes to _temp_content property
  3. Calls batch_embeddings_for_nodes() which:
    - Batch looks up ChromaDB cache
    - Sends uncached items to OpenAI parallel embeddings
    - Writes embeddings back to Neo4j
  4. Cleans up _temp_content property

  7C. Post-chunk (end of historical processing, run_event_trader.py:410)

  After all Redis checks pass (chunk complete):
  - Calls neo4j_processor.batch_process_qaexchange_embeddings(batch_size, max_items=None)
  - Same batch flow as 7B above

  ---
  STAGE 8: Lifecycle Tracking & Cleanup

  Meta Hash (tracking:meta:transcripts:{id}):

  Each transcript gets a Redis hash tracking its lifecycle:
  - ingested_at — when first stored as raw
  - source_api_timestamp — conference datetime from API
  - processed_at — when moved from raw to processed
  - inserted_into_neo4j_at — when written to Neo4j (clears any earlier filtered_at/failed_at)
  - filtered_at + reason — if filtered (e.g., no valid symbols)
  - failed_at + reason — if processing failed

  Pending Set (tracking:pending:transcripts):

  - Added on ingested_at
  - Removed on inserted_into_neo4j_at, filtered_at, or failed_at

  Auto Transcript Cleaner Scripts (eventReturns/auto_transcript_cleaner*.sh):

  - Monitors chunk log files for stuck transcripts
  - Queries Neo4j via cypher-shell to check if transcript has complete INFLUENCES relationships (all 12 return fields across 4
  entity types)
  - Deletes fully-processed transcripts from Redis raw keys via kubectl

  Fix Stuck Transcripts (scripts/fix_stuck_raw_transcripts.py):

  - Scans for transcripts:hist:raw:* keys not in the raw queue
  - Re-pushes them to transcripts:queues:raw for reprocessing

  ---
  Complete Neo4j Graph Structure

  (Company) -[:HAS_TRANSCRIPT]-> (Transcript)
  (Transcript) -[:INFLUENCES]-> (Company)     [with stock/sector/industry/macro returns]
  (Transcript) -[:INFLUENCES]-> (Sector)      [with sector returns]
  (Transcript) -[:INFLUENCES]-> (Industry)    [with industry returns]
  (Transcript) -[:INFLUENCES]-> (MarketIndex) [with macro returns]
  (Transcript) -[:HAS_PREPARED_REMARKS]-> (PreparedRemark)
  (Transcript) -[:HAS_QA_EXCHANGE]-> (QAExchange)  [with embedding vector]
  (QAExchange) -[:NEXT_EXCHANGE]-> (QAExchange)     [linked list order]
  (Transcript) -[:HAS_QA_SECTION]-> (QuestionAnswer) [fallback]
  (Transcript) -[:HAS_FULL_TEXT]-> (FullTranscriptText) [fallback]

  ---
  Key Redis Key Patterns

  ┌──────────────────────────────────────────────┬───────────────────────────────────────────┐
  │                   Pattern                    │                  Purpose                  │
  ├──────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ transcripts:live:raw:{id}                    │ Live raw transcript                       │
  ├──────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ transcripts:hist:raw:{id}                    │ Historical raw transcript                 │
  ├──────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ transcripts:queues:raw                       │ Raw processing queue (list)               │
  ├──────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ transcripts:{live|hist}:processed:{id}       │ Processed transcript                      │
  ├──────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ transcripts:queues:processed                 │ Processed queue (list)                    │
  ├──────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ transcripts:pending_returns                  │ Sorted set for return scheduling          │
  ├──────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ transcripts:withreturns:{id}                 │ Enriched with stock returns               │
  ├──────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ transcripts:withoutreturns:{id}              │ Returns unavailable                       │
  ├──────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ tracking:meta:transcripts:{id}               │ Lifecycle tracking hash                   │
  ├──────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ tracking:pending:transcripts                 │ Set of pending items                      │
  ├──────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ admin:transcripts:schedule                   │ Sorted set of live scheduled fetches      │
  ├──────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ admin:transcripts:processed                  │ Set of already-processed live transcripts │
  ├──────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ batch:transcripts:{from}-{to}:fetch_complete │ Historical batch completion flag          │
  └──────────────────────────────────────────────┴───────────────────────────────────────────┘

  ---
  Notable Nuances

  0. CRITICAL: Transcript ingestion has LLM-in-the-loop — GPT-4o for speaker classification (every transcript, before Redis),
  GPT-4o-mini for QA filler filtering (during Neo4j insertion). News ingestion has NO LLM dependency. Both models are being
  retired by OpenAI — must migrate to successor models before re-enabling transcripts. See GAP-20.
  1. Only ReportsManager is still disabled in DataManagerCentral (BENZINGA_ONLY mode) — news and transcripts are active.
  Transcripts re-enabled 2026-03-03 (commit fd7bfd4). Search "BENZINGA_ONLY" for all 5 locations to re-enable reports.
  2. Standalone CLI path exists: scripts/process_transcripts.sh → Neo4jProcessor.py transcripts → process_transcript_data() —
  can process directly from Redis to Neo4j without the full pipeline
  3. Two Q&A boundary detection methods with 3-level fallback chain
  4. LLM substantiality filter on short QA exchanges prevents filler (greetings, "thank you") from becoming nodes
  5. Double embedding paths: PubSub generates per-item, batch generates in bulk — both check embedding IS NULL to avoid
  duplicates
  6. Fiscal-to-calendar mapping uses company-specific fiscal_year_end_month from the stock universe CSV
  7. Transcript ID format is DATETIME: `AAPL_2025-07-31T17.00` — consistent across Redis keys, data blob, and Neo4j nodes.
  `get_transcript_key_id()` and `_standardize_fields()` both produce this format (fixed 2026-03-03, see `done_fixes/transcript-fix.md`).
  8. QAExchange IDs use double underscore: {transcript_id}_qa__{sequence} — only counting substantial (non-filler) exchanges in
   the sequence counter
  9. ChromaDB serves as embedding cache — content-hashed for deduplication across transcript reruns
  10. The withreturns key is only deleted after verifying inserted_into_neo4j_at exists in meta hash — preventing data loss if
  Neo4j write fails

  ---
  Open Items (carried from transcript-fix.md GAPs, 2026-03-03)

  BLOCKING:
  - GAP-20: OpenAI model retirement — GPT-4o (`feature_flags.py:140`, speaker classification at `EarningsCallTranscripts.py:483`)
    and GPT-4o-mini (`feature_flags.py:131`, QA filler filter at `transcript.py:41,68`) are being retired.
    Both use OpenAI Responses API with structured JSON output. Must replace with successor models before
    re-enabling transcript ingestion. `feature_flags.py:130` has a commented-out `gpt-4.1-mini` reference.

  FUTURE / DEFERRED:
  - GAP-18: Same-day transcript collision guard. Theoretical — zero occurrences across 4,192 transcripts.
    If two conferences happen same day for same company, MERGE silently overwrites first with second.
    Proposed fix (not validated): check `conference_datetime` in `_process_deduplicated_transcript` before
    MERGE, append `_2` suffix on mismatch. Implement only if it ever occurs.

  OPTIONAL CLEANUP:
  - GAP-15: `publish_transcript_update()` at `ReturnsProcessor.py:342-351` — confirmed dead code (zero callers).
    Active method is `_publish_news_update()`. Safe to delete.
  - GAP-16: `parse_transcript_key_id()` at `redis_constants.py:76-91` — confirmed dead code (zero callers).
    Safe to delete.

  ---
  GAP-19: Re-enable Transcript Ingestion — DONE (2026-03-03)

  STATUS: COMPLETED. Transcripts enabled independent of reports (commits 5f732b8 + fd7bfd4).

  WHAT WAS DONE (2026-03-03):

  Commit 5f732b8 — Fix transcript schedule key format:
    All 4 manual transcript ID constructions replaced with canonical get_transcript_key_id():
    1. config/DataManagerCentral.py:491 — schedule ZSET key (was LONG, now DATETIME)
    2. redisDB/TranscriptProcessor.py:129 — _transcript_exists key_id
    3. redisDB/TranscriptProcessor.py:263 — _handle_transcript_found key_id
    4. redisDB/TranscriptProcessor.py:360 — _standardize_fields id field

  Commit fd7bfd4 — Enable transcript ingestion independent of reports:
    1. config/DataManagerCentral.py:693 — uncommented TranscriptsManager source
    2. config/DataManagerCentral.py:727 — uncommented process_transcript_data() (already-initialized branch)
    3. config/DataManagerCentral.py:744 — uncommented process_transcript_data() (fresh-init branch)
    4. scripts/run_event_trader.py:199 — removed SOURCE_REPORTS from gap-fill monitor (would hang forever)
    5. scripts/run_event_trader.py:306 — added SOURCE_TRANSCRIPTS to historical chunk monitor
    6. neograph/mixins/reconcile.py:132 — fixed early return that skipped transcript reconciliation
       when no report keys exist (changed `return results` to `if/else` guard)

  TO RE-ENABLE REPORTS IN THE FUTURE (search "BENZINGA_ONLY" for all 5 locations):
    1. config/DataManagerCentral.py:692 — uncomment self.sources['reports'] = ReportsManager(...)
    2. config/DataManagerCentral.py:726 — uncomment self.process_report_data()
    3. config/DataManagerCentral.py:743 — uncomment self.process_report_data()
    4. scripts/run_event_trader.py:200 — add SOURCE_REPORTS back to gap-fill sources list
    5. scripts/run_event_trader.py:306 — add SOURCE_REPORTS back to historical chunk sources list
    No reconcile.py edit needed — the if/else guard supports both states.

  Quick verification: rg -n "BENZINGA_ONLY" config/DataManagerCentral.py scripts/run_event_trader.py

  KNOWN LIMITATIONS OF CURRENT ARCHITECTURE (applies to ALL sources, not just transcripts):
  - Single process: if it OOMs or the machine reboots, all ingestion stops until watchdog restarts
  - Daemon threads: a crashed thread dies silently — main process stays alive, watchdog sees "running"
  - No per-thread health checks — only process-level liveness via pgrep
  - No retry/dead-letter for individual items (Redis queues provide crash recovery, not item-level retry)
  - No horizontal scaling — one machine, one process
  - Watchdog is bash-based (pgrep + PID file), not K8s liveness/readiness probes

  These limitations are acceptable at current scale (news runs 24/7 without issues). If reliability
  requirements increase (e.g., trading signals depend on real-time transcript availability), consider
  the K8s migration below as a future project covering ALL sources, not just transcripts.

  FUTURE: Full Ingestion Pipeline K8s Migration (all sources)
  If/when the thread-based architecture proves insufficient for 24/7 trading:

  Option A — Minimal K8s (wrap existing code):
    Deploy `run_event_trader.py` as a K8s Deployment (replicas=1) with liveness probe.
    Gains: auto-restart on crash/OOM, node failure recovery, resource limits.
    Doesn't fix: silent thread death, no per-source scaling.
    Effort: ~2 hours (YAML + healthcheck endpoint)

  Option B — Full decomposition (queue-per-item, KEDA-native):
    Separate each source into its own Deployment. Decompose into queue-driven workers.
    Tricky part: ReturnsProcessor is inherently delayed (1hr/1session/1day) — doesn't fit
    queue-per-item cleanly. Needs separate always-on pod or CronJob for pending returns.
    Gains: per-source restart, horizontal scaling, retry/dead-letter, proper health checks.
    Effort: ~2-3 days (decompose TranscriptsManager + ReturnsProcessor + new worker scripts + YAMLs)

  No action needed now. Revisit if/when the thread-based architecture causes actual production issues.

  HIGHER PRIORITY THAN K8s MIGRATION:
  The failure mode that matters for trading is "data stops flowing and I don't notice." The fix for
  that isn't K8s pods — it's monitoring and alerting. A Grafana alert catches every failure mode
  (thread death, process crash, API outage, Redis down) regardless of deployment model.

  Recommended actions (in priority order):
  1. Grafana alert for stale data (~30 min) — highest bang for buck
     Alert if zero new News/Transcript nodes in Neo4j in the last N minutes.
     Catches ALL failure modes. Existing Prometheus/Grafana stack at :32000 is ready.
  2. Thread-level heartbeat (~1 hour)
     Each daemon thread writes a Redis key with its last-active timestamp (e.g.,
     `heartbeat:news:processor`, `heartbeat:news:returns`, `heartbeat:news:websocket`).
     A simple check script or Grafana query flags dead threads even when the process is alive.
  3. GAP-20 model swap (transcripts are already enabled)

  Total: ~2.5 hours to get transcripts running with real alerting — vs. 2-3 days for K8s migration
  that solves the same visibility problem less directly.