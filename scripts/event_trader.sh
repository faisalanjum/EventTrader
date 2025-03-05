#!/bin/bash
# EventTrader Control Script
# Usage: ./scripts/event_trader.sh {start|start-all|stop|status|restart|logs|monitor|stop-monitor|stop-all|clean-logs|health} [options] [from-date] [to-date]

# Configuration
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS_DIR="$WORKSPACE_DIR/logs"
SCRIPT_PATH="$WORKSPACE_DIR/scripts/run_event_trader.py"
PID_FILE="$WORKSPACE_DIR/event_trader.pid"
MONITOR_PID_FILE="$WORKSPACE_DIR/event_trader_monitor.pid"
LOG_RETENTION_DAYS=7  # Days to keep logs before cleaning

# Parse command line flags
RUN_BACKGROUND=false
ARGS=()
DATE_ARGS=()

# Process all arguments
for arg in "$@"; do
  if [[ "$arg" == "--background" ]]; then
    RUN_BACKGROUND=true
  elif [[ "$arg" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    # This looks like a date
    DATE_ARGS+=("$arg")
  else
    # Regular argument
    ARGS+=("$arg")
  fi
done

# Set command and extract it from args
COMMAND=${ARGS[0]}
ARGS=("${ARGS[@]:1}")  # Remove first element

# Handle date arguments correctly
if [[ ${#DATE_ARGS[@]} -eq 1 ]]; then
  # Only from date provided
  FROM_DATE="${DATE_ARGS[0]}"
  TO_DATE="$(date +%Y-%m-%d)"
elif [[ ${#DATE_ARGS[@]} -eq 2 ]]; then
  # Both dates provided
  FROM_DATE="${DATE_ARGS[0]}"
  TO_DATE="${DATE_ARGS[1]}"
else
  # Default dates (yesterday to today)
  FROM_DATE="$(date -v-1d +%Y-%m-%d)"
  TO_DATE="$(date +%Y-%m-%d)"
fi

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

# Run a command in background if requested
run_in_background() {
  if [ "$RUN_BACKGROUND" = true ]; then
    echo "Running in background mode"
    "$@" > /dev/null 2>&1 &
    return $!
  else
    "$@"
    return $?
  fi
}

# Start EventTrader
start() {
  if is_running; then
    echo "EventTrader is already running (PID: $(cat $PID_FILE))"
    return
  fi
  
  echo "Starting EventTrader ($FROM_DATE to $TO_DATE)..."
  cd "$WORKSPACE_DIR"
  
  if [ "$RUN_BACKGROUND" = true ]; then
    # Start in background - logging handled by log_config.py
    python "$SCRIPT_PATH" --from-date "$FROM_DATE" --to-date "$TO_DATE" > /dev/null 2>&1 &
    PID=$!
  else
    # Start in foreground with output to terminal
    python "$SCRIPT_PATH" --from-date "$FROM_DATE" --to-date "$TO_DATE" &
    PID=$!
  fi
  
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

# Start both EventTrader and monitor
start_all() {
  start
  
  # Only start monitor if EventTrader started successfully
  if is_running; then
    # Wait a moment to let EventTrader initialize
    sleep 3
    monitor "${ARGS[@]}"
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

# Show more detailed health information
health() {
  # First show basic status
  status
  
  echo ""
  echo "=== SYSTEM HEALTH ==="
  
  # Check CPU and memory usage
  if is_running; then
    PID=$(cat "$PID_FILE" 2>/dev/null || pgrep -f "python.*run_event_trader.py")
    echo "EventTrader process stats:"
    ps -p $PID -o %cpu,%mem,rss,vsz | head -1
    ps -p $PID -o %cpu,%mem,rss,vsz | grep -v CPU
  fi
  
  # Check log growth
  echo ""
  echo "Log file sizes:"
  du -h $(find "$LOGS_DIR" -type f -name "*.log" | sort -r | head -n 5) 2>/dev/null || echo "No log files found"
  
  # Check disk space
  echo ""
  echo "Disk space:"
  df -h . | grep -v Filesystem
  
  # Check Redis if available
  if command -v redis-cli >/dev/null 2>&1; then
    echo ""
    echo "Redis status:"
    redis-cli ping 2>/dev/null || echo "Redis connection failed"
    redis-cli info | grep used_memory_human 2>/dev/null || echo "Could not get Redis memory usage"
  fi
}

# Start the monitor/watchdog
monitor() {
  MAX_RESTARTS=${ARGS[0]:-5}   # Default 5 restarts
  CHECK_INTERVAL=${ARGS[1]:-60} # Default 60 seconds
  
  if is_monitor_running; then
    echo "Watchdog is already running (PID: $(cat $MONITOR_PID_FILE 2>/dev/null || pgrep -f "watchdog.sh"))"
    return
  fi
  
  echo "Starting EventTrader Watchdog (Max restarts: $MAX_RESTARTS, Check interval: ${CHECK_INTERVAL}s)..."
  cd "$WORKSPACE_DIR"
  
  if [ "$RUN_BACKGROUND" = true ]; then
    # Start watchdog in the background without output
    "$WORKSPACE_DIR/scripts/watchdog.sh" $MAX_RESTARTS $CHECK_INTERVAL > /dev/null 2>&1 &
    WATCHDOG_PID=$!
    echo "Watchdog started in background with PID $WATCHDOG_PID"
  else
    # Start watchdog in the background but with output visible
    "$WORKSPACE_DIR/scripts/watchdog.sh" $MAX_RESTARTS $CHECK_INTERVAL &
    WATCHDOG_PID=$!
    echo "Watchdog started with PID $WATCHDOG_PID"
  fi
  
  echo "$WATCHDOG_PID" > "$MONITOR_PID_FILE"
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

# Clean old log files
clean_logs() {
  days=${ARGS[0]:-$LOG_RETENTION_DAYS}
  echo "Cleaning log files older than $days days..."
  
  # Find and count files to be removed
  old_files=$(find "$LOGS_DIR" -type f -name "*.log" -mtime +$days)
  count=$(echo "$old_files" | grep -v "^$" | wc -l)
  
  if [ $count -eq 0 ]; then
    echo "No log files older than $days days found"
    return
  fi
  
  echo "Found $count files to clean:"
  echo "$old_files" | xargs ls -lh | awk '{print $9, "(" $5 ")"}'
  
  # Ask for confirmation if running interactively
  if [ "$RUN_BACKGROUND" = false ] && [ -t 0 ]; then
    read -p "Delete these files? (y/n): " confirm
    if [[ "$confirm" != [yY]* ]]; then
      echo "Operation cancelled"
      return
    fi
  fi
  
  # Delete old files
  find "$LOGS_DIR" -type f -name "*.log" -mtime +$days -delete
  echo "Cleaned $count log files"
}

# Process command
case "$COMMAND" in
  start)
    start
    ;;
  start-all)
    start_all
    ;;
  stop)
    stop
    ;;
  restart)
    stop
    sleep 2
    start
    ;;
  restart-all)
    stop_monitor
    stop
    sleep 2
    start_all
    ;;
  status)
    status
    ;;
  health)
    health
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
    monitor
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
  clean-logs)
    # Clean old log files
    clean_logs
    ;;
  *)
    echo "Usage: $0 [--background] {command} [options] [from-date] [to-date]"
    echo ""
    echo "Commands:"
    echo "  start                        # Start EventTrader"
    echo "  start-all                    # Start both EventTrader and watchdog"
    echo "  stop                         # Stop EventTrader"
    echo "  restart                      # Restart EventTrader"
    echo "  restart-all                  # Restart both EventTrader and watchdog"
    echo "  status                       # Show status and recent logs"
    echo "  health                       # Show detailed system health information"
    echo "  logs                         # Show more detailed logs"
    echo "  monitor [max_restarts] [interval]  # Start watchdog"
    echo "  stop-monitor                 # Stop the watchdog"
    echo "  stop-all                     # Stop both watchdog and EventTrader"
    echo "  clean-logs [days]            # Clean log files older than specified days"
    echo ""
    echo "Options:"
    echo "  --background                 # Run commands in background mode"
    echo ""
    echo "Examples:"
    echo "  $0 start                        # Start with yesterday to today"
    echo "  $0 start 2025-03-04 2025-03-05  # Start with specific dates" 
    echo "  $0 --background start-all       # Start everything in background"
    echo "  $0 monitor 10 120               # Start watchdog with 10 max restarts, 120s check interval"
    echo "  $0 clean-logs 14                # Clean logs older than 14 days"
    exit 1
    ;;
esac

exit 0 