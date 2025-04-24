# run the Neo4j initialization from the command line
./scripts/event_trader.sh init-neo4j

# specify date ranges and run it in the background
./scripts/event_trader.sh --background init-neo4j --from-date 2024-01-01 --to-date 2024-03-31 

**The init_neo4j() function in event_trader.sh initializes the Neo4j database by:**
1. Detecting the Python interpreter
2. Running run_event_trader.py with the --neo4j-init-only flag to set up the database
3. Directly running the Neo4jInitializer module to ensure date nodes are created

init_neo4j() in event_trader.sh
├── detect_python() - Determines Python interpreter path
├── $PYTHON_CMD "$SCRIPT_PATH" with --neo4j-init-only flag
│   ├── run_event_trader.py main()
│   │   ├── parse_args() - Processes command line args
│   │   ├── setup_logging() - Configures logging
│   │   ├── load_dotenv() - Loads environment variables
│   │   ├── EventTrader initialization
│   │   │   ├── EventTrader.__init__(args)
│   │   │   │   ├── initialize_redis() - Sets up Redis connections
│   │   │   │   ├── initialize_database() - Sets up database connections
│   │   │   │   └── initialize_data_manager() - Prepares data sources
│   │   │   └── EventTrader.ensure_neo4j_initialized()
│   │   │       ├── get_manager() - Gets Neo4jManager singleton
│   │   │       ├── Neo4jManager.initialize_database()
│   │   │       │   ├── Neo4jManager.connect() - Establishes Neo4j connection
│   │   │       │   ├── Neo4jInitializer initialization
│   │   │       │   │   └── Neo4jInitializer.__init__(neo4j_manager)
│   │   │       │   └── Neo4jInitializer.initialize_database()
│   │   │       │       ├── create_constraints() - Creates Neo4j constraints
│   │   │       │       ├── create_indexes() - Sets up database indexes
│   │   │       │       ├── create_initial_entities()
│   │   │       │       │   ├── create_sectors() - Creates sector nodes
│   │   │       │       │   ├── create_industries() - Creates industry nodes
│   │   │       │       │   ├── create_market_indices() - Creates market index nodes
│   │   │       │       │   └── create_companies() - Creates company nodes
│   │   │       │       └── create_relationships()
│   │   │       │           ├── create_company_relationships() - Links companies to sectors/industries
│   │   │       │           └── create_market_relationships() - Links companies to markets
│   │   │       └── Neo4jManager.close() - Closes Neo4j connection if not needed
│   │   └── exit() - Exits script after initialization
└── $PYTHON_CMD -m neograph.Neo4jInitializer --start_date "$FROM_DATE"
    ├── Neo4jInitializer.__main__ entry point
    │   ├── parse_args() - Processes command line arguments
    │   ├── get_manager() - Gets Neo4j connection singleton 
    │   ├── Neo4jInitializer(neo4j_manager) - Creates initializer instance
    │   └── Neo4jInitializer.create_dates(start_date, end_date)
    │       ├── create_single_date() - Creates individual date nodes
    │       │   ├── _create_date_node() - Creates a date node with properties
    │       │   └── _create_next_relationship() - Creates NEXT relationship to next date
    │       ├── add_price_relationships_to_dates()
    │       │   ├── fetch_prices() - Gets price data for date range
    │       │   └── create_price_relationships_batch() - Creates price relationships
    │       ├── create_dividends()
    │       │   ├── fetch_dividend_data() - Gets dividend data
    │       │   ├── create_single_dividend() - Creates dividend nodes
    │       │   └── _create_dividend_relationships() - Links dividends to dates and companies
    │       └── create_splits()
    │           ├── fetch_split_data() - Gets stock split data
    │           ├── create_single_split() - Creates split nodes
    │           └── _create_split_relationships() - Links splits to dates and companies