# EventTrader Operation Guide

## Core Operations

1. Starting the System:

   ```bash
   ./scripts/event_trader.sh start                    # Start EventTrader only
   ./scripts/event_trader.sh start-all               # Start EventTrader and watchdog together
   ./scripts/event_trader.sh --background start-all  # Run everything in background
   ```
   
   With date ranges:
   ```bash
   ./scripts/event_trader.sh start 2025-03-04 2025-03-05
   ```
   ## -historical - Enable only historical data (disable live data)
   ./scripts/event_trader.sh --background start-all -historical 2025-02-01 2025-02-10

2. Monitoring:

   ```bash
   ./scripts/event_trader.sh status  # Basic status and recent logs
   ./scripts/event_trader.sh logs    # Last 50 log lines
   ./scripts/event_trader.sh health  # Detailed system health information
   ```

3. Stopping/Restarting:

   ```bash
   ./scripts/event_trader.sh stop       # Stop EventTrader only
   ./scripts/event_trader.sh stop-all   # Stop both EventTrader and watchdog
   ./scripts/event_trader.sh restart    # Restart EventTrader
   ./scripts/event_trader.sh restart-all # Restart both EventTrader and watchdog
   ```


4. Running Neo4jProcessor Independently:

'''
# Initialize database
./scripts/neo4j_processor.sh init                    # Initialize Neo4j database
./scripts/neo4j_processor.sh init --verbose          # Initialize with detailed logging

# Process news items
./scripts/neo4j_processor.sh news --max 10           # Process up to 10 news items
./scripts/neo4j_processor.sh news --batch 20         # Process in batches of 20 items

# Process SEC reports
./scripts/neo4j_processor.sh reports --max 10        # Process up to 10 report items
./scripts/neo4j_processor.sh reports --verbose       # Process reports with detailed logging

# Combined operations
./scripts/neo4j_processor.sh all                     # Initialize and process all data
./scripts/neo4j_processor.sh all --max 5             # Process only 5 items of each type
./scripts/neo4j_processor.sh all --skip-news         # Process only reports
./scripts/neo4j_processor.sh all --skip-reports      # Process only news


--verbose, -v                  # Enable detailed logging
--batch N                      # Set batch size (default: 10)
--max N                        # Limit number of items to process (0 for all)
--skip-without-returns         # Process only items with returns data
--force, -f                    # Continue despite non-critical errors


5. XBRL Status by Report Type

./scripts/xbrl_status_report.py




## Watchdog Management

The watchdog monitors EventTrader and automatically restarts it if it crashes.

```bash
./scripts/event_trader.sh monitor           # Start watchdog with default settings
./scripts/event_trader.sh monitor 10 120    # Custom settings (10 max restarts, 120s interval)
./scripts/event_trader.sh stop-monitor      # Stop watchdog only
```

## Maintenance

```bash
./scripts/event_trader.sh clean-logs       # Clean logs older than 7 days
./scripts/event_trader.sh clean-logs 14    # Clean logs older than 14 days
```

## Quick Reference

| Command | Description |
|---------|-------------|
| `start` | Start EventTrader |
| `start-all` | Start EventTrader + watchdog |
| `--background` | Run in background (add before command) |
| `stop` | Stop EventTrader |
| `stop-all` | Stop EventTrader + watchdog |
| `restart-all` | Restart everything |
| `status` | Check system status |
| `health` | Detailed system health |
| `logs` | View recent logs |
| `clean-logs [days]` | Remove old logs |

All commands support date ranges: `./scripts/event_trader.sh command [from-date] [to-date]` 