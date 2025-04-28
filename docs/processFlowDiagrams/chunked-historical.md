(To be thoroughly checked - )
prompt: "Inside @run_event_trader.py and @event_trader.sh you can see all start up processes that chunked-historical calls starting from @DataManagerCentral.py - First I want you to list all of the methods, classes, functions - including all nested operations inside each function"


1. Entry Point - event_trader.sh:

    chunked-historical command
    └── process_chunked_historical() function
        ├── Reads config from feature_flags.py (HISTORICAL_CHUNK_DAYS, HISTORICAL_STABILITY_WAIT_SECONDS)
        └── For each chunk date range:
            └── Calls run_event_trader.py with -historical flag

2. run_event_trader.py

    main()
    ├── parse_args()
    ├── DataManager initialization
    │   └── DataManager.__init__(date_from, date_to)
    │       ├── initialize_sources()
    │       │   ├── BenzingaNewsManager(historical_range)
    │       │   ├── ReportsManager(historical_range)
    │       │   └── TranscriptsManager(historical_range)
    │       └── initialize_neo4j()
    │           └── Neo4jProcessor initialization and setup
    └── manager.start()
        └── Starts all source managers


3. Source Managers (BenzingaNewsManager, ReportsManager, TranscriptsManager):

    BenzingaNewsManager.start()
    ├── rest_client.get_historical_data()
    ├── processor.process_all_news() (in thread)
    └── returns_processor.process_all_returns() (in thread)

    ReportsManager.start()
    ├── rest_client.get_historical_data() (in thread)
    ├── processor.process_all_reports() (in thread)
    └── returns_processor.process_all_returns() (in thread)

    TranscriptsManager.start()
    ├── _initialize_transcript_schedule()
    ├── processor.process_all_transcripts() (in thread)
    ├── returns_processor.process_all_returns() (in thread)
    └── _fetch_historical_data() (in thread)
        └── earnings_call_client.get_transcripts_for_single_date()


4. Processor Classes:

    NewsProcessor.process_all_news()
    ├── process_raw_news()
    └── process_news_returns()

    ReportProcessor.process_all_reports()
    ├── process_raw_reports()
    └── process_report_returns()

    TranscriptProcessor.process_all_transcripts()
    ├── process_raw_transcripts()
    └── process_transcript_returns()

    ReturnsProcessor.process_all_returns()
    ├── process_pending_returns()
    └── process_returns_for_item()


5. Neo4j Processing:

    Neo4jProcessor
    ├── process_with_pubsub() (continuous thread)
    ├── process_news_to_neo4j()
    ├── process_reports_to_neo4j()
    ├── process_transcripts_to_neo4j()
    └── batch_process_qaexchange_embeddings()

6. Redis Operations (Throughout):

    EventTraderRedis
    ├── RedisClient operations
    │   ├── RAW_QUEUE operations
    │   ├── PROCESSED_QUEUE operations
    │   └── FAILED_QUEUE operations
    └── Redis PubSub operations for Neo4j processing



***************************************************************************************************************************

## Chunked Historical Processing Flow

### 1. Entry Point: event_trader.sh in Detail
- **[event_trader.sh](../../scripts/event_trader.sh)**: Bash script control interface
  - `chunked-historical` command
    - **Command validation**:
      - Checks that required FROM_DATE is provided
      - Uses default TO_DATE (today) if not specified
      - Verifies date format (YYYY-MM-DD)
      
    - **`process_chunked_historical()` function execution**:
      - **Configuration loading**:
        - Calls `detect_python()` to find Python interpreter
        - Loads `HISTORICAL_CHUNK_DAYS` and `HISTORICAL_STABILITY_WAIT_SECONDS` from `config/feature_flags.py`
        - Validates configuration values are positive integers
        
      - **Logging setup**:
        - Creates single combined log file: `logs/chunked_historical_${FROM_DATE}_to_${TO_DATE}.log`
        - Defines `shell_log()` function for consistent logging
        - Logs initialization message
        
      - **System checks**:
        - Verifies Redis connectivity with `redis-cli ping`
        - Logs available data sources (news, reports, transcripts)
        - Records total start time for duration tracking
        
      - **Date chunking**:
        - Converts date strings to Unix timestamps (OS-specific compatibility)
        - Creates chunks based on `HISTORICAL_CHUNK_DAYS` configuration
        - Initializes chunk counter
        
      - **Processing loop** (for each chunk):
        - Records chunk start time
        - Calculates chunk start/end dates
        - Logs current chunk information
        - Executes `stop-all` to terminate previous instances
        - Calls `detect_python()` to ensure Python interpreter
        - **Runs Python processor**:
          ```
          $PYTHON_CMD "$SCRIPT_PATH" \
            --from-date "$chunk_start" \
            --to-date "$chunk_end" \
            -historical \
            --ensure-neo4j-initialized \
            --log-file "$COMBINED_LOG_FILE"
          ```
        - Captures Python exit code
        - Handles success/failure scenarios
        - Executes `stop-all` to ensure clean state between chunks
        - Calculates and logs chunk duration
        - Advances to next chunk start date
        
      - **Finalization**:
        - Calculates and logs total process duration
        - Logs completion message with full range processed

### 2. Python Application Startup in Detail
- **[run_event_trader.py](../../scripts/run_event_trader.py)**: Main Python entry point
  - **`main()` function**:
    - **Error handling setup**: Wraps execution in try-except to catch critical errors
    - **Command-line processing**:
      - `parse_args()`: Processes command-line arguments
        - Parses `--from-date` and `--to-date` (required)
        - Handles `-historical` flag to disable live data
        - Processes `--ensure-neo4j-initialized` flag
        - Configures `--log-file` path
    - **Feature flag configuration**:
      - Sets `ENABLE_HISTORICAL_DATA=True` (for chunked-historical mode)
      - Sets `ENABLE_LIVE_DATA=False` (historical only)
    - **Logging initialization**:
      - Sets up logging framework
      - Creates designated log file for this chunk
    - **Signal handlers**:
      - Registers handlers for SIGINT/SIGTERM for clean shutdown
    - **DataManager creation**:
      - Initializes manager with date range: `manager = DataManager(date_from, date_to)`
    - **Neo4j validation**:
      - Verifies Neo4j connection with `manager.has_neo4j()`
      - Proceeds if initialized, exits with error if failed
    - **System startup**:
      - Calls `manager.start()` to begin processing
      - Waits for completion in historical-only mode

### 3. Data Manager Initialization in Detail
- **DataManager.__init__(date_from, date_to)**:
  - **Core initialization**:
    - Sets up logger
    - Stores date range in `historical_range` dictionary
    - Creates empty `sources` dictionary
  - **Source initialization**:
    - `initialize_sources()`: Creates source manager instances
      - `BenzingaNewsManager(historical_range)`: News data source
        - Initializes Redis connection for news
        - Creates NewsProcessor instance
        - Sets up ReturnsProcessor for news
      - `ReportsManager(historical_range)`: SEC filings source
        - Initializes Redis connection for reports
        - Creates ReportProcessor instance
        - Sets up ReturnsProcessor for reports
      - `TranscriptsManager(historical_range)`: Earnings calls source
        - Initializes Redis connection for transcripts
        - Creates TranscriptProcessor instance
        - Sets up ReturnsProcessor for transcripts
  - **Neo4j initialization**:
    - `initialize_neo4j()`: Sets up graph database connection
      - Creates Neo4jProcessor instance
      - Initializes database if needed (creates constraints, indexes)
      - Creates date nodes for the date range
      - Starts background processing thread via `process_with_pubsub()`
  - **Signal handler setup**:
    - Registers handlers for graceful shutdown

### 4. DataManager Start Process
- **manager.start()**: Main method that triggers all processing
  - Calls `start()` on each source manager:
    - **BenzingaNewsManager.start()**:
      - `rest_client.get_historical_data()`: Fetches data in historical mode
      - `processor.process_all_news()`: Spawns processing thread
      - `returns_processor.process_all_returns()`: Spawns returns thread
    - **ReportsManager.start()**:
      - `rest_client.get_historical_data()`: Fetches data in historical mode
      - `processor.process_all_reports()`: Spawns processing thread
      - `returns_processor.process_all_returns()`: Spawns returns thread
    - **TranscriptsManager.start()**:
      - `_initialize_transcript_schedule()`: Sets up retrieval plan
      - `processor.process_all_transcripts()`: Spawns processing thread
      - `returns_processor.process_all_returns()`: Spawns returns thread
      - `_fetch_historical_data()`: Retrieves transcript data in historical mode
  - Returns dictionary of status results from all source starts

### 5. Runtime Operation Mode Differences

#### Historical Mode (`-historical` flag)
- **Feature Flags Set**:
  - `ENABLE_HISTORICAL_DATA = True` 
  - `ENABLE_LIVE_DATA = False`
- **Data Source Behavior**:
  - Each manager retrieves data only for the specified date range
  - No WebSocket connections are established
  - No live data listeners are started
- **Completion Monitoring**:
  - System runs until all historical data is processed
  - Monitors Redis for completion indicators:
    - `fetch_complete` flags for all sources
    - Empty raw queues
    - Empty pending returns sets
    - Empty WithReturns/WithoutReturns namespaces
  - Periodically checks status every 30 seconds
  - Logs completion status for each source
- **Finalization**:
  - Triggers QA embeddings generation after all processing completes
  - Calls `manager.stop()` to shut down cleanly
  - Exits Python process with success code
  - Returns control to bash script for next chunk

#### Chunked Historical Mode (via `chunked-historical` command)
- **Operational Difference**:
  - Uses `-historical` flag internally
  - Breaks full date range into smaller chunks based on `HISTORICAL_CHUNK_DAYS`
  - Processes each chunk as a separate Python process execution
  - Creates individual log files for each chunk
  - Tracks and aggregates results across all chunks
- **Between-Chunk Operations**:
  - Stops all EventTrader processes between chunks 
  - Cleans up system state
  - Creates fresh process environment for each chunk
  - Prevents memory leaks and resource exhaustion
  - Allows for parallel processing of disjoint date ranges

#### Live Mode (`-live` flag)
- **Feature Flags Set**:
  - `ENABLE_HISTORICAL_DATA = False`
  - `ENABLE_LIVE_DATA = True`
- **Data Source Behavior**:
  - Benzinga WebSocket is established for real-time news
  - SEC WebSocket is established for real-time filings
  - No historical data retrieval is performed
  - No date range restrictions are applied
- **Runtime Pattern**:
  - System runs indefinitely in continuous processing mode
  - Enters infinite loop with simple 60-second status checks
  - No completion monitoring or exit conditions
  - Requires manual stop or signal to terminate
- **Not Used in Chunked Historical**:
  - `-live` flag is incompatible with `chunked-historical` processing
  - Shell script explicitly uses `-historical` for all chunks

#### Default Mode (no flags)
- **Feature Flags Set**:
  - `ENABLE_HISTORICAL_DATA = True`
  - `ENABLE_LIVE_DATA = True`
- **Behavior**:
  - Both historical retrieval and live WebSockets are active
  - Processes historical data for specified range
  - Continues running indefinitely for live data
  - No automatic completion or exit

### Thread Execution By Mode

The following table shows which threads are started (✅) or not started (🚫) in each mode:

| Thread | Live Mode (-live) | Chunked-Historical (-historical) |
|--------|-------------------|----------------------------------|
| processor_thread (News) | ✅ | ✅ |
| returns_thread (News) | ✅ | ✅ |
| ws_thread (News WebSocket) | ✅ | 🚫 |
| historical_thread (News Historical Fetch) | 🚫 | ✅ |
| processor_thread (Reports) | ✅ | ✅ |
| returns_thread (Reports) | ✅ | ✅ |
| ws_thread (Reports WebSocket) | ✅ | 🚫 |
| historical_thread (Reports Historical Fetch) | 🚫 | ✅ |
| processor_thread (Transcripts) | ✅ | ✅ |
| returns_thread (Transcripts) | ✅ | ✅ |
| ws_thread (Transcripts) | 🚫 | 🚫 |
| historical_thread (Transcripts Historical Fetch) | 🚫 | ✅ |
| neo4j_thread (PubSub Event Processor) | ✅ | ✅ |

**Key Details:**
- Processor and returns threads run in all modes to handle data processing
- WebSocket threads only run in live mode (except Transcripts which don't use WebSockets)
- Historical fetch threads only run in historical mode
- Neo4j PubSub processor runs in all modes to handle data integration

### Neo4j PubSub Event-Driven Architecture

The `neo4j_thread` runs the PubSub processor that moves data from Redis to Neo4j. Here's exactly what happens:

#### Concrete PubSub Steps

1. **Channel Setup**:
   - Creates Redis PubSub connection 
   - Subscribes to 6 specific channels:
     ```
     news:withreturns  
     news:withoutreturns
     reports:withreturns
     reports:withoutreturns
     transcripts:withreturns
     transcripts:withoutreturns
     ```

2. **Initial Processing**:
   - Immediately processes existing Redis data:
     ```python
     # Batch sizes configured for different data types
     process_news_to_neo4j(batch_size=50)
     process_reports_to_neo4j(batch_size=50)
     process_transcripts_to_neo4j(batch_size=5)
     ```

3. **Continuous Event Listening**:
   - Waits for messages with a short timeout (0.1s)
   - When a message arrives, identifies content type (news/reports/transcripts)
   - Triggers `_process_pubsub_item()` with appropriate parameters
   - Performs hourly reconciliation to catch any missed items

4. **Item Processing**:
   - Retrieves item data from Redis using consistent key format
   - Processes item through the appropriate method:
     ```python
     _process_deduplicated_news()
     _process_deduplicated_report()
     _process_deduplicated_transcript()
     ```
   - Generates embeddings where applicable
   - Deletes processed Redis keys to prevent reprocessing

#### Exact Live vs. Historical Differences

| Live Mode | Chunked-Historical Mode |
|-----------|-------------------------|
| Messages come from WebSockets as data arrives | Messages come from historical processors as they complete batches |
| PubSub runs indefinitely | PubSub stops when chunk processing is complete |
| Small bursts of processing (few items at a time) | Large batches processed together (entire date ranges) |
| Items have varied processing times | Items processed in rapid succession |
| News embeddings generated immediately | Embeddings batch-generated at end of processing |
| Key expiry handled with TTL | Keys explicitly deleted after processing |

#### Raw Redis Channel Structure

```
# Example message on news:withreturns channel
{
  "channel": "news:withreturns",
  "data": "news_12345"  # Item ID to be processed
}
```

#### Inter-Thread Communication

For chunked-historical mode specifically:
1. Historical fetch thread adds data to Redis
2. Processor threads process raw data
3. Returns processor calculates market impact
4. Redis publish notifies PubSub thread data is ready
5. PubSub thread processes data into Neo4j
6. Primary thread monitors for completion flags

This event-driven model ensures data flows through the system without blocking operations.

### 6. Data Processing Pipeline
- **NewsProcessor**
  - `process_all_news()`: Main processing function
    - `process_raw_news()`: Converts raw data to structured format
    - `process_news_returns()`: Analyzes market impact

- **ReportProcessor**
  - `process_all_reports()`: Main processing function
    - `process_raw_reports()`: Converts raw data to structured format
    - `process_report_returns()`: Analyzes market impact

- **TranscriptProcessor**
  - `process_all_transcripts()`: Main processing function
    - `process_raw_transcripts()`: Converts raw data to structured format
    - `process_transcript_returns()`: Analyzes market impact

- **ReturnsProcessor**
  - `process_all_returns()`: General returns processing
    - `process_pending_returns()`: Handles the queue
    - `process_returns_for_item()`: Individual item processing

### 7. Neo4j Graph Database Storage
- **Neo4jProcessor**
  - `process_with_pubsub()`: Continuous background thread
  - `process_news_to_neo4j()`: News-specific storage
  - `process_reports_to_neo4j()`: SEC report storage
  - `process_transcripts_to_neo4j()`: Transcript storage
  - `batch_process_qaexchange_embeddings()`: Generates embeddings

### 8. Redis Operations
- **EventTraderRedis**
  - `RedisClient` operations:
    - `RAW_QUEUE` management
    - `PROCESSED_QUEUE` management
    - `FAILED_QUEUE` management
  - Redis PubSub for Neo4j processing coordination


***************************************************************************************************************************