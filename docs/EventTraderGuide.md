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