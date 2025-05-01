# EventTrader Workflows

This document summarizes the main execution workflows for the EventTrader system and provides links to relevant call graph diagrams.

## Workflows at a Glance

| Mode               | CLI Example                                                                   | Flags passed to run_event_trader.py             | Core Path Entry Points in `run_event_trader.py`                       | Notes                                      |
| :----------------- | :---------------------------------------------------------------------------- | :---------------------------------------------- | :-------------------------------------------------------------------- | :----------------------------------------- |
| **Chunked-Historical** | `./scripts/event_trader.sh chunked-historical 2024-01-01 2024-02-01`        | `-historical` (passed for each date chunk)     | `main()` -> `DataManager.start()` -> Historical loop (Redis checks) -> Embeddings -> `manager.stop()` -> `sys.exit(0)` | Processes data in date ranges sequentially |
| **Live**           | `./scripts/event_trader.sh start-all -live 2025-03-01`                        | `-live`                                         | `main()` -> `DataManager.start()` -> Live loop (`while True: time.sleep(60)`) | Runs indefinitely                          |
| **Gap-Fill**       | `./scripts/event_trader.sh start -historical 2025-03-01 2025-03-02 --gap-fill` | `-historical --gap-fill`                        | `main()` -> `DataManager.start()` -> `monitor_gap_fill()` -> `manager.stop()` -> `sys.exit(0)` | Fetches/processes initial data, then exits |

## Core Component Interactions

Based on analysis of `run_event_trader.py` and `DataManagerCentral.py`:

**Initialization (Common to all workflows):**
1.  `run_event_trader.main()` -> `DataManager.__init__()`
2.  `DataManager.__init__()` calls:
    *   `initialize_sources()`: Creates instances of `BenzingaNewsManager`, `ReportsManager`, `TranscriptsManager`.
    *   `initialize_neo4j()`: Creates `Neo4jProcessor`, connects, initializes DB if needed (using `Neo4jInitializer`), starts `neo4j_processor.process_with_pubsub()` thread.

**Starting Pipelines (`DataManager.start()` called by `run_event_trader.main()`):**
*   `DataManager.start()` iterates and calls `start()` on each source manager (`BenzingaNewsManager`, `ReportsManager`, `TranscriptsManager`).

**Workflow-Specific Threads/Calls (Triggered by Source Manager `start()` methods):**

*   **Historical Mode Active (`-historical` flag):**
    *   `BenzingaNewsManager.start()` -> `BenzingaNewsRestAPI.get_historical_data()`
    *   `ReportsManager.start()` -> `historical_thread` runs `SECRestAPI.get_historical_data()`
    *   `TranscriptsManager.start()` -> `historical_thread` runs `_fetch_historical_data` (uses `EarningsCallProcessor`)
    *   *Also starts Processor & Returns threads (see below)*

*   **Live Mode Active (`-live` flag):**
    *   `BenzingaNewsManager.start()` -> `ws_thread` runs `_run_websocket` (uses `BenzingaNewsWebSocket`)
    *   `ReportsManager.start()` -> `ws_thread` runs `_run_websocket` (uses `SECWebSocket`)
    *   `TranscriptsManager.start()` -> Calls `_initialize_transcript_schedule` (uses `EarningsCallProcessor`)
    *   *Also starts Processor & Returns threads (see below)*

*   **Common Processing Threads (Started by Source Managers regardless of flags):**
    *   `NewsProcessor.process_all_news()`
    *   `ReportProcessor.process_all_reports()`
    *   `TranscriptProcessor.process_all_transcripts()`
    *   `ReturnsProcessor.process_all_returns()` (called by all 3 source managers)
    *   `Neo4jProcessor.process_with_pubsub()` (started during `DataManager` init)

## Call Graphs (PDF)

*   [Overall Static Graph (SVG)](call_graphs/EventTrader_Core_callgraph.svg) - *Note: Very large*
*   DataManager ([PDF](link_to_datamanager.pdf)) - *TODO*
*   Historical Processing Components ([PDF](link_to_historical.pdf)) - *TODO*
*   Live Processing Components ([PDF](link_to_live.pdf)) - *TODO*

*(Links to be added after focused graph generation)* 