# EventTrader Operation Guide

## Core Operations

### Starting the System

There are two primary ways to start the system:

**A) Standard Start (`start` / `start-all`):**

   Use this for default operation or live-only/historical-only runs covering a *single, specific date range*.

   ```bash
   # Default: Runs BOTH historical (last 3 days) AND live data continuously
   ./scripts/event_trader.sh start
   ./scripts/event_trader.sh start-all # Includes watchdog

   # Historical ONLY: Processes the specified range as ONE batch, then EXITS
   ./scripts/event_trader.sh start -historical 2025-03-01 2025-03-10 

   # Live ONLY: Runs live streams continuously (specify start date for Neo4j init)
   ./scripts/event_trader.sh start -live 2025-04-21
   
   # Run in background
   ./scripts/event_trader.sh --background start-all 
   ```
   *   Without `-historical` or `-live`, it enables both modes and the main process runs indefinitely.
   *   With `-historical`, it runs *only* the historical processing for the given range and the main process exits automatically after internal Redis monitoring confirms completion.
   *   With `-live`, it runs *only* the live data streams and the main process runs indefinitely.

**B) Chunked Historical Processing (`chunked-historical`):**

   Use this command *specifically* for processing **large historical date ranges** sequentially in smaller, manageable chunks. **Do not use standard `start -historical` for very large ranges.**

   ```bash
   # Process from specified start date up to today in default chunks
   ./scripts/event_trader.sh chunked-historical YYYY-MM-DD 

   # Process a specific large date range in default chunks
   ./scripts/event_trader.sh chunked-historical YYYY-MM-DD YYYY-MM-DD
   ```
   *   This command internally runs the Python script in `-historical` mode for each chunk.
   *   It waits for Python to confirm processing completion (via Redis monitoring) for one chunk, stops all processes, then starts the next chunk.
   *   Chunk size and stability wait times are configured in `config/feature_flags.py`.
   *   Creates a single combined log file for the entire run.

### Monitoring

   ```bash
   ./scripts/event_trader.sh status  # Basic status and recent logs
   ./scripts/event_trader.sh logs    # Last 50 log lines (from default log or chunked log if running)
   ./scripts/event_trader.sh health  # Detailed system health information
   ```

### Stopping/Restarting

   ```bash
   ./scripts/event_trader.sh stop       # Stop EventTrader only
   ./scripts/event_trader.sh stop-all   # Stop both EventTrader and watchdog
   ./scripts/event_trader.sh restart    # Restart EventTrader
   ./scripts/event_trader.sh restart-all # Restart both EventTrader and watchdog
   ```

### Running Neo4jProcessor Independently

   This script (`./scripts/neo4j_processor.sh`) acts as a convenient wrapper around the main Python processor logic (`neograph/Neo4jProcessor.py`) for tasks like initializing the database or batch-processing specific data types directly from Redis into Neo4j, bypassing the main EventTrader application flow.

   **Note:** Using this wrapper script automatically enables verbose logging (`--verbose`) for the underlying Python script.

   ```bash
   # Initialize database
   ./scripts/neo4j_processor.sh init                    # Initialize Neo4j database (verbose)

   # Process news items
   ./scripts/neo4j_processor.sh news --max 10           # Process up to 10 news items (verbose)
   ./scripts/neo4j_processor.sh news --batch 20         # Process news in batches of 20 (verbose)

   # Process SEC reports
   ./scripts/neo4j_processor.sh reports --max 10        # Process up to 10 report items (verbose)

   # Combined operations
   ./scripts/neo4j_processor.sh all                     # Initialize and process all data (verbose)
   ./scripts/neo4j_processor.sh all --max 5             # Process only 5 items of each type (verbose)
   ./scripts/neo4j_processor.sh all --skip-news         # Process only reports and transcripts (verbose)
   ./scripts/neo4j_processor.sh all --skip-reports      # Process only news and transcripts (verbose)

   # Other options passed directly to the Python script:
   # --batch N                      # Set batch size (default: 10)
   # --max N                        # Limit number of items to process (0 for all)
   # --skip-without-returns         # Process only items with returns data
   # --force, -f                    # Continue despite non-critical errors
   # --skip-transcripts             # Skip processing transcripts in 'all' mode
   # --start-date YYYY-MM-DD        # Start date for date nodes during 'init' (default: 2017-09-01)
   ```

### XBRL Status Report

   ```bash
   ./scripts/xbrl_status_report.py # Display XBRL processing status summary
   ```

## Watchdog Management


## Partial Reset - Preserved Neo4j Initilization nodes/relationships + also redis stocks univers:

./scripts/event_trader.sh partial-reset


# Generate snapshot of all nodes and relationships in Neo4j report
./scripts/event_trader.sh neo4j-report
./scripts/neo4j_terminal_report.sh