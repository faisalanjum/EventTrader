#!/bin/bash
# Simple EventTrader Control Script
# Usage: ./scripts/run.sh start|stop|status [from-date] [to-date]

# Set paths
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS_DIR="$WORKSPACE_DIR/logs"
SCRIPT_PATH="$WORKSPACE_DIR/scripts/run_event_trader.py"

# Default dates (yesterday to today)
FROM_DATE="${2:-$(date -v-1d +%Y-%m-%d)}"
TO_DATE="${3:-$(date +%Y-%m-%d)}"

# Ensure logs directory exists
mkdir -p "$LOGS_DIR"

# Make Python script executable 
chmod +x "$SCRIPT_PATH"

# Check if running
is_running() {
  pgrep -f "python.*run_event_trader.py" > /dev/null
}

# Find the most recent log file
get_latest_log() {
  find "$LOGS_DIR" -type f -name "event_trader_*.log" -o -name "eventtrader_*.log" | sort -r | head -n 1
}

# Start EventTrader
start() {
  if is_running; then
    echo "EventTrader is already running"
    return
  fi
  
  echo "Starting EventTrader ($FROM_DATE to $TO_DATE)..."
  cd "$WORKSPACE_DIR"
  
  # Start in background - logging handled by log_config.py
  python "$SCRIPT_PATH" --from-date "$FROM_DATE" --to-date "$TO_DATE" > /dev/null 2>&1 &
  
  PID=$!
  echo "EventTrader started with PID $PID"
  
  # Wait a moment to verify it's running
  sleep 2
  if ! is_running; then
    echo "WARNING: Process may have failed to start. Check logs in $LOGS_DIR"
    LATEST_LOG=$(get_latest_log)
    if [ -n "$LATEST_LOG" ]; then
      tail -n 10 "$LATEST_LOG"
    fi
  fi
}

# Stop EventTrader
stop() {
  if ! is_running; then
    echo "EventTrader is not running"
    return
  fi
  
  PID=$(pgrep -f "python.*run_event_trader.py")
  echo "Stopping EventTrader (PID: $PID)..."
  
  # Send SIGTERM for graceful shutdown
  kill -TERM $PID
  
  # Wait for process to exit
  for i in {1..10}; do
    if ! is_running; then
      echo "EventTrader stopped successfully"
      return
    fi
    echo -n "."
    sleep 1
  done
  echo ""
  
  # If still running after 10 seconds, force kill
  if is_running; then
    echo "Force killing EventTrader process..."
    kill -9 $PID
  fi
}

# Show status
status() {
  if is_running; then
    PID=$(pgrep -f "python.*run_event_trader.py")
    UPTIME=$(ps -o etime= -p "$PID")
    echo "EventTrader is running (PID: $PID, Uptime: $UPTIME)"
    
    # Show the most recent log file
    LATEST_LOG=$(get_latest_log)
    
    # Show the latest logs
    echo ""
    echo "Recent log entries:"
    if [ -n "$LATEST_LOG" ]; then
      echo "=== $(basename "$LATEST_LOG") ==="
      tail -n 15 "$LATEST_LOG"
    else
      echo "No recent log files found"
    fi
    
    # Show websocket status if available
    echo ""
    echo "WebSocket connections:"
    grep -i "websocket" "$LATEST_LOG" 2>/dev/null | tail -n 10 || echo "No WebSocket activity found in logs"
  else
    echo "EventTrader is not running"
  fi
}

# Process command
case "$1" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  restart)
    stop
    sleep 2
    start
    ;;
  status)
    status
    ;;
  logs)
    # Display more complete logs
    LATEST_LOG=$(get_latest_log)
    if [ -n "$LATEST_LOG" ]; then
      echo "Showing last 50 lines from $(basename "$LATEST_LOG"):"
      tail -n 50 "$LATEST_LOG"
    else
      echo "No log files found"
    fi
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs} [from-date] [to-date]"
    echo "Examples:"
    echo "  $0 start                        # Start with yesterday to today"
    echo "  $0 start 2025-03-04 2025-03-05  # Start with specific dates" 
    echo "  $0 logs                         # Show more detailed logs"
    exit 1
    ;;
esac

exit 0 