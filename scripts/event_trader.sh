#!/bin/bash
# EventTrader Control Script
# Usage: ./scripts/event_trader.sh {start|stop|status|restart|logs|monitor|stop-monitor} [from-date] [to-date]

# Configuration
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS_DIR="$WORKSPACE_DIR/logs"
SCRIPT_PATH="$WORKSPACE_DIR/scripts/run_event_trader.py"
PID_FILE="$WORKSPACE_DIR/event_trader.pid"
MONITOR_PID_FILE="$WORKSPACE_DIR/event_trader_monitor.pid"

# Default dates (yesterday to today)
FROM_DATE="${2:-$(date -v-1d +%Y-%m-%d)}"
TO_DATE="${3:-$(date +%Y-%m-%d)}"

# Ensure log directory exists
mkdir -p "$LOGS_DIR"

# Make Python script executable 
chmod +x "$SCRIPT_PATH"

# Find most recent log file
get_latest_log() {
  find "$LOGS_DIR" -type f -name "event_trader_*.log" -o -name "eventtrader_*.log" | sort -r | head -n 1
}

# Check if EventTrader is running
is_running() {
  # Check PID file first
  if [ -f "$PID_FILE" ]; then
    pid=$(cat "$PID_FILE")
    if ps -p "$pid" > /dev/null 2>&1; then
      return 0  # Running from PID file
    fi
  fi
  
  # Fallback: Look for running process
  if pgrep -f "python.*run_event_trader.py" > /dev/null 2>&1; then
    # Get PID and update PID file
    pid=$(pgrep -f "python.*run_event_trader.py")
    echo $pid > "$PID_FILE"
    return 0  # Running from process check
  fi
  
  # Not running
  return 1
}

# Check if monitor/watchdog is running
is_monitor_running() {
  # Check monitor PID file
  if [ -f "$MONITOR_PID_FILE" ]; then
    pid=$(cat "$MONITOR_PID_FILE")
    if ps -p "$pid" > /dev/null 2>&1; then
      return 0  # Running from PID file
    fi
  fi
  
  # Fallback: Look for running watchdog
  if pgrep -f "watchdog.sh" > /dev/null 2>&1; then
    # Get PID and update PID file
    pid=$(pgrep -f "watchdog.sh")
    echo $pid > "$MONITOR_PID_FILE"
    return 0  # Running from process check
  fi
  
  # Not running
  return 1
}

# Start EventTrader
start() {
  if is_running; then
    echo "EventTrader is already running (PID: $(cat $PID_FILE))"
    return
  fi
  
  echo "Starting EventTrader ($FROM_DATE to $TO_DATE)..."
  cd "$WORKSPACE_DIR"
  
  # Start in background - logging handled by log_config.py
  python "$SCRIPT_PATH" --from-date "$FROM_DATE" --to-date "$TO_DATE" > /dev/null 2>&1 &
  
  PID=$!
  echo "$PID" > "$PID_FILE"
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
  
  PID=$(cat "$PID_FILE")
  echo "Stopping EventTrader (PID: $PID)..."
  
  # Send SIGTERM for graceful shutdown
  kill -TERM $PID 2>/dev/null
  
  # Wait for process to exit
  for i in {1..10}; do
    if ! is_running; then
      echo "EventTrader stopped successfully"
      rm -f "$PID_FILE" 2>/dev/null
      return
    fi
    echo -n "."
    sleep 1
  done
  echo ""
  
  # If still running after 10 seconds, force kill
  if is_running; then
    echo "Force killing EventTrader process..."
    kill -9 $(cat "$PID_FILE") 2>/dev/null
    rm -f "$PID_FILE" 2>/dev/null
  fi
}

# Show status
status() {
  if is_running; then
    PID=$(cat "$PID_FILE" 2>/dev/null || pgrep -f "python.*run_event_trader.py")
    UPTIME=$(ps -o etime= -p "$PID" 2>/dev/null | tr -d ' ')
    echo "EventTrader is running (PID: $PID, Uptime: $UPTIME)"
    
    # Show monitor status
    if is_monitor_running; then
      echo "Watchdog monitor is active (PID: $(cat $MONITOR_PID_FILE 2>/dev/null || pgrep -f "watchdog.sh"))"
    else
      echo "Watchdog monitor is not active"
    fi
    
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
    if [ -n "$LATEST_LOG" ]; then
      grep -i "websocket" "$LATEST_LOG" 2>/dev/null | tail -n 10 || echo "No WebSocket activity found in logs"
    fi
  else
    echo "EventTrader is not running"
    
    # Show monitor status
    if is_monitor_running; then
      echo "Watchdog monitor is active (PID: $(cat $MONITOR_PID_FILE 2>/dev/null || pgrep -f "watchdog.sh"))"
    else
      echo "Watchdog monitor is not active"
    fi
  fi
}

# Start the monitor/watchdog
monitor() {
  MAX_RESTARTS=${2:-5}   # Default 5 restarts
  CHECK_INTERVAL=${3:-60} # Default 60 seconds
  
  if is_monitor_running; then
    echo "Watchdog is already running (PID: $(cat $MONITOR_PID_FILE 2>/dev/null || pgrep -f "watchdog.sh"))"
    return
  fi
  
  echo "Starting EventTrader Watchdog (Max restarts: $MAX_RESTARTS, Check interval: ${CHECK_INTERVAL}s)..."
  cd "$WORKSPACE_DIR"
  
  # Start watchdog in the background
  "$WORKSPACE_DIR/scripts/watchdog.sh" $MAX_RESTARTS $CHECK_INTERVAL > /dev/null 2>&1 &
  
  WATCHDOG_PID=$!
  echo "$WATCHDOG_PID" > "$MONITOR_PID_FILE"
  echo "Watchdog started with PID $WATCHDOG_PID"
}

# Stop the monitor/watchdog
stop_monitor() {
  if ! is_monitor_running; then
    echo "Watchdog is not running"
    return
  fi
  
  pid=$(cat "$MONITOR_PID_FILE" 2>/dev/null || pgrep -f "watchdog.sh")
  echo "Stopping watchdog (PID: $pid)..."
  kill -TERM $pid 2>/dev/null
  rm -f "$MONITOR_PID_FILE" 2>/dev/null
  echo "Watchdog stopped"
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
  monitor)
    # Start watchdog mode with optional parameters
    monitor "$2" "$3"
    ;;
  stop-monitor)
    # Stop the watchdog
    stop_monitor
    ;;
  stop-all)
    # Stop both watchdog and main process
    stop_monitor
    stop
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs|monitor|stop-monitor|stop-all} [from-date] [to-date]"
    echo "Examples:"
    echo "  $0 start                        # Start with yesterday to today"
    echo "  $0 start 2025-03-04 2025-03-05  # Start with specific dates" 
    echo "  $0 logs                         # Show more detailed logs"
    echo "  $0 monitor                      # Start watchdog with default settings"
    echo "  $0 monitor 10 120               # Start watchdog with 10 max restarts, 120s check interval"
    exit 1
    ;;
esac

exit 0 
exit 0 