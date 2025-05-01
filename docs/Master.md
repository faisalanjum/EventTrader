# EventTrader Documentation

### 1. Entry Points

1. **chunked-historical** — `chunked-historical FROM_DATE TO_DATE`
2. **gap-fill** — `start[-all] -historical FROM_DATE TO_DATE --gap-fill`
3. **live** — `start[-all] -live START_DATE`
> *run via* `./scripts/event_trader.sh`

---

### 2. Chunked-historical Workflow

<details><summary>Flow Diagram</summary>

```
chunked-historical {from_date} {to_date}
   │
   ├── Chunk 1: Process days 1-5
   │   └── Monitor completion via Redis state
   │
   ├── Chunk 2: Process days 6-10
   │   └── Monitor completion via Redis state
   │
   └── Chunk N: Process remaining days
       └── Monitor completion via Redis state
```
</details>

1. **High-level flow**  
   1. Bash script entry → `event_trader.sh chunked-historical`  
   2. Date chunking → 5 days per chunk (default)  
   3. Sequential processing → Launches separate Python processes for each chunk  
   4. Completion monitoring → Python monitors Redis for processing completion  
   5. Clean state → [`stop-all`](#stop-all-process) → Ensures clean system termination between chunks  
   6. Embedding generation → Triggers vector embedding creation after processing  
   7. Reconciliation → Handles edge cases where items remain stuck

2. **Bash command details** <details><summary>validation & configuration</summary>

   - **Command validation**:
     - Checks that required FROM_DATE is provided
     - Uses default TO_DATE (today) if not specified
     - Verifies date format (YYYY-MM-DD)
        
   - **Configuration loading**:
     - Calls `detect_python()` to find Python interpreter
     - Loads `HISTORICAL_CHUNK_DAYS` and `HISTORICAL_STABILITY_WAIT_SECONDS` from **feature_flags.py**
     - Validates configuration values are positive integers

   </details>

3. **Logging & system preparation** <details><summary>setup details</summary>

   - **Logging setup**:
     - Creates unique folder `logs/ChunkHist_{FROM_DATE}_to_{TO_DATE}_{TIMESTAMP}/`
     - Creates separate log files:
       - Combined shell log file for tracking overall process
       - Individual log file for each chunk's Python process
     - Defines `shell_log()` function to write to shell log
     - Shell logs are written to combined file while Python logs go to chunk-specific files
        
   - **System checks**:
     - Verifies Redis connectivity with `redis-cli ping` > **TODO — before starting each chunk, print all redis namespaces + neo4j nodes & relationships count by types**
     - Logs available data sources (news, reports, transcripts) > **To Check**
     - Record total start time for duration tracking
        
   - **Date chunking**:
     - Converts date strings to Unix timestamps (OS-specific compatibility)
     - Creates chunks based on `HISTORICAL_CHUNK_DAYS` configuration
     - Initializes chunk counter and monitoring variables

   </details>

4. **Per-chunk processing loop** <details><summary>run & monitor</summary>

   - **Chunk initialization**:
     - Records chunk start time
     - Calculates chunk start/end dates
     - Creates chunk-specific log file
     - Executes [`stop-all`](#stop-all-process) to terminate previous instances
   
   - **Python processor execution**:
     <details><summary>Launch command</summary>
     
     ```bash
     $PYTHON_CMD "$SCRIPT_PATH" \
         --from-date "$chunk_start" \
         --to-date "$chunk_end" \
         -historical \
         --ensure-neo4j-initialized \
         --log-file "$CHUNK_LOG_FILE"
     ```
     </details>
     
     > [`--ensure-neo4j-initialized`](#neo4j-initialization-process) ensures proper Neo4j database setup for each chunk.
   
   - **Process monitoring**:
     - Captures and stores Python PID: `EVENTTRADER_PID=$!`
     - Writes PID to file for external tracking
     - Monitors process with timeout controls:
       - Watches for completion messages in log files (searches for "Historical chunk processing finished" or "Shutdown complete" text patterns)
       - Periodically checks if process is still running via PID
       - Times out after 2 hours maximum per chunk (sets MAX_WAIT=7200 seconds, increments ELAPSED counter each check interval, logs warning message if timeout reached, marks process as failed, then forcefully terminates it)
   
   - **Process termination** (if needed):
     - First attempts graceful shutdown with [`SIGTERM`](#unix-signals)
     - Waits 5 seconds for clean exit
     - Forces termination with [`SIGKILL`](#unix-signals) if process remains
   
   - **Chunk finalization**:
     - Captures Python exit code
     - Extracts key events (errors, warnings, completions) from chunk log (uses `grep -E "ERROR|WARNING|CRITICAL|successfully|completed|failed"` to filter important messages)
     - Appends summary to combined log file
     - Executes [`stop-all`](#stop-all-process) to ensure clean state between chunks
     - Calculates and logs chunk duration
     - Advances to next chunk start date

   </details>

5. **Finalization process** <details><summary>summary & cleanup</summary>

   - Calculates and logs total process duration
   - Creates summary file with statistics (creates a summary.txt file in the log folder using shell redirection `{} > "$SUMMARY_FILE"`; contents include: date range processed, run timestamp, total chunks count, total processing time in seconds, and configuration settings for chunk size and stability wait; confirms creation with "Summary file created" message)
   - Logs completion message with full range processed

   </details>

6. **Python Application** <details><summary>run_event_trader.py</summary>

   1. **Main Python Entry Point**  
      [`run_event_trader.py`](../../scripts/run_event_trader.py) is the core entry script that orchestrates the full data processing lifecycle.

   <details><summary>main() function flow</summary>

   - **Error handling setup**: 
   - Comprehensive try-except block for entire application
   - Graceful shutdown on errors with detailed logging

   - **Command-line processing**:
   - `parse_args()` handles CLI flags:
      - Parses `--from-date` and `--to-date` (required)
      - Handles `-historical` flag to disable live data
      - Processes `--ensure-neo4j-initialized` flag
      - Accepts `--log-file` path (chunk-specific log)

   - **Feature flag configuration**:
   - Sets `ENABLE_HISTORICAL_DATA=True` (for chunked-historical mode)
   - Sets `ENABLE_LIVE_DATA=False` (disables live processing)

   - **Logging initialization**:
   - Sets up logging framework with file and console handlers
   - Writes to chunk-specific log file provided by shell script

   - **Signal handlers**:
   - Registers handlers for SIGINT/SIGTERM for clean shutdown

   - **DataManager creation**:
   - Initializes with date range: `manager = DataManager(date_from, date_to)`

   - **Neo4j validation**:
   - Verifies connection using `manager.has_neo4j()`
   - Exits on failure, proceeds on success

   - **System startup**:
   - Calls `manager.start()` to launch ingestion system
   - Enters monitoring loop for historical-only mode

   </details>


   2. **Completion Monitoring**  
      Applies only in historical mode. Uses Redis state and flags to detect when all items are processed.

   <details><summary>Redis-based completion checks</summary>

   - Helper functions:
   - `check_initial_processing()` → Validates early-stage fetch and queue state
   - `only_withreturns_remain()` → Detects when only post-return items remain
   
   - Monitors multiple Redis indicators per source:
   1. `batch:{source}:{from}-{to}:fetch_complete`
   2. `{source}:queues:raw`
   3. `{source}:hist:{raw|processed}:*`
   4. `{source}:pending_returns`
   5. `{source}:withreturns:*`
   6. `{source}:withoutreturns:*`

   - Checks every 30 seconds
   - Includes timeout logic (`WITHRETURNS_MAX_RETRIES`)
   - Triggers reconciliation if stalled on withreturns
   - Logs per-source completion state

   </details>

   3. **Post-Processing: Embedding Generation**  
      Initiates vector embeddings after all chunk processing is done.

   <details><summary>Semantic embedding phase</summary>

   - Calls `neo4j_processor.batch_process_qaexchange_embeddings()`
   - Uses batch size from `QAEXCHANGE_EMBEDDING_BATCH_SIZE`
   - Targets QA pairs for semantic enrichment
   - Enables search & relationship discovery downstream

   </details>

   4. **Shutdown Sequence**  
      Performs full system cleanup and exits with success.

   <details><summary>Final shutdown and handoff</summary>

   - Calls `manager.stop()` for clean exit
   - Logs: `"Shutdown complete. Exiting Python process"`
   - Exit code `0` returned to shell
   - Bash script resumes and advances to next chunk

   </details>

---

### 4. Support Processes

1. **stop-all** <details><summary>termination sequence</summary>
   <a id="stop-all-process"></a>
   
   The `stop-all` command ensures complete termination of all system components:

   1. **Stop Watchdog Monitor**:
      - Identifies running watchdog process via PID file or `pgrep`
      - Sends [`SIGTERM`](#unix-signals) signal for graceful termination
      - Removes monitor PID file

   2. **Stop EventTrader Main Process**:
      - Identifies running process via PID file or `pgrep`
      - Sends [`SIGTERM`](#unix-signals) signal for graceful shutdown
      - Waits up to 10 seconds for process to exit
      - Force kills with [`SIGKILL`](#unix-signals) if still running after timeout
      - Removes main PID file

   3. **Verification & Cleanup**:
      - Waits 1 second for processes to terminate
      - Checks if any components are still running:
        - `run_event_trader.py` processes
        - `Neo4jInitializer` processes
        - `watchdog.sh` processes

   4. **Force Termination** (if needed):
      - If any processes remain running, executes complete cleanup:
        - Finds and terminates all Neo4jInitializer processes with [`SIGKILL`](#unix-signals)
        - Finds and terminates all EventTrader processes with [`SIGKILL`](#unix-signals)
        - Finds and terminates all watchdog processes with [`SIGKILL`](#unix-signals)
        - Removes all PID files

   > This ensures a clean system state between processing chunks, preventing resource leaks and ensuring each chunk starts in a fresh environment.

   </details>

2. **Neo4j initialization** <details><summary>[`--ensure-neo4j-initialized`](#neo4j-initialization-process)</summary>
   <a id="neo4j-initialization-process"></a>

   The [`--ensure-neo4j-initialized`](#neo4j-initialization-process) flag ensures proper Neo4j database setup:

   1. **Automatic Initialization Flow**:
      - `DataManager` constructor automatically calls `initialize_neo4j()`
      - `initialize_neo4j()` creates a Neo4jProcessor instance
      - Neo4jProcessor sets up database schema (constraints and indexes)
      - Creates date nodes for the processing date range
      - Starts Neo4j background processor thread
      - `has_neo4j()` verifies successful connection

   2. **Flag Behavior**:
      - Script verifies initialization success via `has_neo4j()`
      - With [`--ensure-neo4j-initialized`](#neo4j-initialization-process): Logs success and continues processing
      - Without flag: Still initializes but doesn't specifically log success
      - If initialization fails: Exits with error regardless of flag

   3. **Comparison with Related Flags**:
      - [`--neo4j-init-only`](#neo4j-initialization-process): Initializes Neo4j and exits immediately
      - [`--ensure-neo4j-initialized`](#neo4j-initialization-process): Initializes Neo4j and continues processing

   4. **Importance in Chunked Processing**:
      - Guarantees each chunk has proper database setup
      - Ensures database is in consistent state after previous [`stop-all`](#stop-all-process)
      - Prevents processing failures due to database connectivity issues
      - Creates required schema elements for the date range being processed

   </details>

3. **Unix signals** <details><summary>signal reference</summary>
   <a id="unix-signals"></a>

   | Signal | Number | Purpose | Can Be Caught | Exit Message |
   |--------|--------|---------|---------------|-------------|
   | [`SIGTERM`](#unix-signals) | 15 | Standard termination | ✅ Yes | "Received signal 15, initiating shutdown" |
   | [`SIGKILL`](#unix-signals) | 9 | Forced termination | ❌ No | None (immediate) |
   | [`SIGINT`](#unix-signals) | 2 | User interrupt (Ctrl+C) | ✅ Yes | "Keyboard interrupt received" |
   | [`SIGHUP`](#unix-signals) | 1 | Terminal disconnect | ✅ Yes | "Hangup detected" |
   | [`SIGQUIT`](#unix-signals) | 3 | Terminal quit (Ctrl+\\\\) | ✅ Yes | Generates core dump |
   | [`SIGABRT`](#unix-signals) | 6 | Abnormal termination | ✅ Yes | "Aborted" |

   **Signal Handler Registration**:
   ```python
   signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
   signal.signal(signal.SIGTERM, signal_handler) # kill command
   ```

   **Normal vs. Error Terminations**:

   | Exit Message | Context | Normal? | Signal | What It Means |
   |--------------|---------|---------|--------|---------------|
   | "Received signal 15, initiating shutdown" | During [`stop-all`](#stop-all-process) between chunks | ✅ Normal | [`SIGTERM`](#unix-signals) | Planned termination |
   | "Received signal 15, initiating shutdown" | Middle of chunk processing | ❌ Error | [`SIGTERM`](#unix-signals) | Unexpected termination |
   | "Keyboard interrupt received" | Testing/development | ✅ Normal | [`SIGINT`](#unix-signals) | Intentional user termination |
   | "Keyboard interrupt received" | Production processing | ❌ Error | [`SIGINT`](#unix-signals) | Accidental Ctrl+C |
   | "Shutdown complete. Exiting" | End of chunk/after signal | ✅ Normal | None | Clean process shutdown |
   | "Historical chunk processing finished" | End of chunk processing | ✅ Normal | None | Successful completion |
   | No message, just termination | Any time | ❌ Error | [`SIGKILL`](#unix-signals) | Force kill/crash/OOM |

   **Diagnostic Tips**:
   - Normal → [`SIGTERM`](#unix-signals) during planned [`stop-all`](#stop-all-process)
   - User-Initiated → [`SIGINT`](#unix-signals) with "Keyboard interrupt received"
   - Abnormal → Unexpected signals outside normal points → Accidental Ctrl+C, external termination, OOM killer

   > 🔍 Always check message context relative to process lifecycle to determine if expected or error condition.

   </details>

---

### TODOs

> **TODO — Before starting each chunk, print all redis namespaces + neo4j nodes & relationships count by types**  
> **TODO — Verify WITHRETURNS retry logic**  
> **TODO — Complete gap-fill process documentation**

