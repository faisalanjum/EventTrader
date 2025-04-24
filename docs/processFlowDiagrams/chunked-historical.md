
(To be thoroughly checked - )
prompt: "Inside @run_event_trader.py and @event_trader.sh you can see all start up processes that chunked-historical calls starting from @DataManagerCentral.py - First I want you to list all of the methods, classes, functions - atleast 3 or 4 levels nested that this calls"


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
