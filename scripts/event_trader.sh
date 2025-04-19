#!/bin/bash
# EventTrader Control Script
# Usage: ./scripts/event_trader.sh {start|start-all|stop|status|restart|logs|monitor|stop-monitor|stop-all|clean-logs|health|init-neo4j|reset-all} [options] [from-date] [to-date]

# Configuration
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS_DIR="$WORKSPACE_DIR/logs"
SCRIPT_PATH="$WORKSPACE_DIR/scripts/run_event_trader.py"
PID_FILE="$WORKSPACE_DIR/event_trader.pid"
MONITOR_PID_FILE="$WORKSPACE_DIR/event_trader_monitor.pid"
LOG_RETENTION_DAYS=7  # Days to keep logs before cleaning

# Default dates (if not provided)
DEFAULT_FROM_DATE=$(date -v-3d "+%Y-%m-%d" 2>/dev/null || date -d "3 days ago" "+%Y-%m-%d" 2>/dev/null || date "+%Y-%m-%d")
DEFAULT_TO_DATE=$(date "+%Y-%m-%d")

# Help text
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Usage: ./scripts/event_trader.sh [options]"
    echo ""
    echo "Commands:"
    echo "  start                   Start EventTrader only"
    echo "  start-all               Start EventTrader and watchdog together"
    echo "  stop                    Stop EventTrader"
    echo "  status                  Check status of EventTrader components"
    echo "  restart                 Restart EventTrader"
    echo "  logs                    View recent logs"
    echo "  monitor                 Start the watchdog monitor"
    echo "  stop-monitor            Stop only the watchdog monitor"
    echo "  stop-all                Stop both EventTrader and watchdog"
    echo "  clean-logs              Remove old log files"
    echo "  health                  Check system health"
    echo "  init-neo4j              Initialize Neo4j database"
    echo "  reset-all               Stop all components and clear data"
    echo ""
    echo "Options:"
    echo "  --background            Run in background mode"
    echo "  --from-date YYYY-MM-DD  Start date for historical data (default: 3 days ago)"
    echo "  --to-date YYYY-MM-DD    End date for historical data (default: today)"
    echo "  -historical             Enable historical data only (disables live)"
    echo "  -live                   Enable live data only (disables historical)"
    echo "  --log-file PATH         Custom log file path"
    echo "  --help, -h              Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./scripts/event_trader.sh start                    # Start EventTrader only (uses 3 days ago to today)"
    echo "  ./scripts/event_trader.sh start-all               # Start EventTrader and watchdog together"
    echo "  ./scripts/event_trader.sh --background start-all  # Run everything in background"
    echo ""
    echo "  With date ranges:"
    echo "  ./scripts/event_trader.sh start 2025-03-04 2025-03-05"
    echo ""
    echo "By default, both historical and live data processing are enabled."
    exit 0
fi

# Check for custom dates
FROM_DATE="$DEFAULT_FROM_DATE"
TO_DATE="$DEFAULT_TO_DATE"

# Process all arguments first for options like --background
for arg in "$@"; do
  if [[ "$arg" == "--background" ]]; then
    RUN_BACKGROUND=true
    break
  fi
done

# Find the appropriate Python executable
detect_python() {
  # Check for virtual environment in the workspace (most reliable)
  if [ -f "$WORKSPACE_DIR/venv/bin/python" ]; then
    PYTHON_CMD="$WORKSPACE_DIR/venv/bin/python"
  # Check if running in a virtual environment
  elif [ -n "$VIRTUAL_ENV" ]; then
    PYTHON_CMD="$VIRTUAL_ENV/bin/python"
  # Try python3 command
  elif command -v python3 > /dev/null 2>&1; then
    PYTHON_CMD="python3"
  # Try python command
  elif command -v python > /dev/null 2>&1; then
    PYTHON_CMD="python"
  # Look for Python in typical locations
  elif [ -f "/usr/bin/python3" ]; then
    PYTHON_CMD="/usr/bin/python3"
  elif [ -f "/usr/local/bin/python3" ]; then
    PYTHON_CMD="/usr/local/bin/python3"
  else
    echo "ERROR: Python interpreter not found. Please install Python or activate your virtual environment."
    exit 1
  fi
  
  echo "Using Python interpreter: $PYTHON_CMD"
  return 0
}

# Parse command line flags - process all arguments
ARGS=()
DATE_ARGS=()

# Process all arguments
for arg in "$@"; do
  if [[ "$arg" == "--background" ]]; then
    # Already handled above
    continue
  elif [[ "$arg" == "-historical" ]]; then
    HISTORICAL_FLAG="-historical"
  elif [[ "$arg" == "-live" ]]; then
    LIVE_FLAG="-live"
  elif [[ "$arg" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    # This looks like a date
    DATE_ARGS+=("$arg")
  else
    # Regular argument - but don't include start-all or other commands here
    if [[ "$arg" != "start" && "$arg" != "start-all" && "$arg" != "stop" && "$arg" != "status" && "$arg" != "restart" && "$arg" != "reset-all" ]]; then
      ARGS+=("$arg")
    fi
  fi
done

# Set command and extract it from args
if [[ ${#ARGS[@]} -gt 0 ]]; then
  COMMAND=${ARGS[0]}
  ARGS=("${ARGS[@]:1}")  # Remove first element
fi

# Determine the command based on positional arguments if not already set
if [[ -z "$COMMAND" ]]; then
  for arg in "$@"; do
    if [[ "$arg" == "start" || "$arg" == "start-all" || "$arg" == "stop" || "$arg" == "status" || "$arg" == "restart" || "$arg" == "reset-all" || "$arg" == "reset-all" ]]; then
      COMMAND="$arg"
      break
    fi
  done
fi

# If still no command, default to start
if [[ -z "$COMMAND" ]]; then
  COMMAND="start"
fi

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
  # Use the default dates set earlier (3 days ago to today)
  FROM_DATE="$DEFAULT_FROM_DATE"
  TO_DATE="$DEFAULT_TO_DATE"
fi

# Log settings after all arguments have been processed
log_settings() {
  echo "==============================================="
  echo "EventTrader Command: $COMMAND"
  echo "Settings:"
  echo "  Date range: $FROM_DATE to $TO_DATE"
  mode="Historical and Live"; [ -n "$HISTORICAL_FLAG" ] && mode="Historical only"; [ -n "$LIVE_FLAG" ] && mode="Live only"; echo "  Mode:      $mode"
  echo "  Background: $([ "$RUN_BACKGROUND" = true ] && echo "Yes" || echo "No")"
  echo "==============================================="
}

# Ensure log directory exists
mkdir -p "$LOGS_DIR"

# Make Python script executable 
chmod +x "$SCRIPT_PATH"

# Log settings before starting
log_settings

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
      # Verify this is our process
      if ps -p "$pid" -o command= | grep -q "run_event_trader.py"; then
        return 0  # Running
      else
        # Not our process - remove stale PID file
        rm -f "$PID_FILE"
      fi
    else
      # Process not running - remove stale PID file
      rm -f "$PID_FILE"
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

# Kill all related EventTrader processes
kill_all_related_processes() {
  echo "Finding and killing all related processes..."
  
  # Kill Neo4jInitializer processes
  neo4j_pids=$(pgrep -f "Neo4jInitializer")
  if [ -n "$neo4j_pids" ]; then
    echo "Killing Neo4jInitializer processes: $neo4j_pids"
    for pid in $neo4j_pids; do
      kill -9 $pid 2>/dev/null
    done
  fi
  
  # Kill run_event_trader.py processes
  event_pids=$(pgrep -f "run_event_trader.py")
  if [ -n "$event_pids" ]; then
    echo "Killing EventTrader processes: $event_pids"
    for pid in $event_pids; do
      kill -9 $pid 2>/dev/null
    done
  fi
  
  # Kill watchdog processes
  watchdog_pids=$(pgrep -f "watchdog.sh")
  if [ -n "$watchdog_pids" ]; then
    echo "Killing watchdog processes: $watchdog_pids"
    for pid in $watchdog_pids; do
      kill -9 $pid 2>/dev/null
    done
  fi
  
  # Remove PID files
  rm -f "$PID_FILE" "$MONITOR_PID_FILE" 2>/dev/null
  
  echo "All related processes have been terminated"
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
  
  # Detect Python before starting
  detect_python
  
  cd "$WORKSPACE_DIR"
  
  # Check if initialization flag should be added
  INIT_FLAG=""
  if [ "${1:-}" = "with_init" ]; then
    INIT_FLAG="--ensure-neo4j-initialized"
    echo "Running with Neo4j initialization check..."
  fi
  
  if [ "$RUN_BACKGROUND" = true ]; then
    # Start in background - logging handled by log_config.py
    $PYTHON_CMD "$SCRIPT_PATH" --from-date "$FROM_DATE" --to-date "$TO_DATE" $HISTORICAL_FLAG $LIVE_FLAG $INIT_FLAG > /dev/null 2>&1 &
    PID=$!
  else
    # Start in foreground with output to terminal
    $PYTHON_CMD "$SCRIPT_PATH" --from-date "$FROM_DATE" --to-date "$TO_DATE" $HISTORICAL_FLAG $LIVE_FLAG $INIT_FLAG &
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
  # Start the main process with initialization flag
  start "with_init"
  
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
    
    # Check one more time and use kill_all_related_processes if needed
    sleep 1
    if pgrep -f "python.*run_event_trader.py" > /dev/null 2>&1; then
      echo "Some EventTrader processes still running, performing forced cleanup..."
      kill_all_related_processes
    fi
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
  
  # Pass through date range and feature flags to watchdog
  WATCHDOG_ARGS="$FROM_DATE $TO_DATE $HISTORICAL_FLAG $LIVE_FLAG"
  
  echo "Starting EventTrader Watchdog (Max restarts: $MAX_RESTARTS, Check interval: ${CHECK_INTERVAL}s)..."
  cd "$WORKSPACE_DIR"
  
  if [ "$RUN_BACKGROUND" = true ]; then
    # Start watchdog in the background without output
    "$WORKSPACE_DIR/scripts/watchdog.sh" $MAX_RESTARTS $CHECK_INTERVAL $WATCHDOG_ARGS > /dev/null 2>&1 &
    WATCHDOG_PID=$!
    echo "Watchdog started in background with PID $WATCHDOG_PID"
  else
    # Start watchdog in the background but with output visible
    "$WORKSPACE_DIR/scripts/watchdog.sh" $MAX_RESTARTS $CHECK_INTERVAL $WATCHDOG_ARGS &
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

# Initialize Neo4j database
init_neo4j() {
  # Detect Python before starting
  detect_python
  
  echo "Initializing Neo4j database..."
  cd "$WORKSPACE_DIR"
  
  # Use run_event_trader.py with our Neo4j flag
  if [ "$RUN_BACKGROUND" = true ]; then
    # Run in background
    $PYTHON_CMD "$SCRIPT_PATH" --from-date "$FROM_DATE" --to-date "$TO_DATE" $HISTORICAL_FLAG $LIVE_FLAG --neo4j-init-only > /dev/null 2>&1 &
    echo "Neo4j initialization started in background"
  else
    # Run in foreground
    $PYTHON_CMD "$SCRIPT_PATH" --from-date "$FROM_DATE" --to-date "$TO_DATE" $HISTORICAL_FLAG $LIVE_FLAG --neo4j-init-only
  fi
  
  # Also directly initialize date nodes with Neo4jInitializer to ensure they're created
  echo "Ensuring date nodes are created..."
  if [ "$RUN_BACKGROUND" = true ]; then
    # Run in background
    $PYTHON_CMD -m neograph.Neo4jInitializer --start_date "$FROM_DATE" > /dev/null 2>&1 &
    # Wait briefly to allow initialization to start
    sleep 2
  else
    # Run in foreground
    $PYTHON_CMD -m neograph.Neo4jInitializer --start_date "$FROM_DATE"
  fi
}

# Process news data into Neo4j
process_news() {
  # Detect Python before starting
  detect_python
  
  echo "Processing news data into Neo4j..."
  cd "$WORKSPACE_DIR"
  
  # Get batch size and max items from arguments
  batch_size=${ARGS[0]:-100}
  max_items=${ARGS[1]:-1000}
  
  # Run the Neo4jProcessor directly
  if [ "$RUN_BACKGROUND" = true ]; then
    # Run in background
    $PYTHON_CMD -c "from neograph.Neo4jProcessor import process_news_data; process_news_data($batch_size, $max_items, True)" > /dev/null 2>&1 &
    echo "News processing started in background"
  else
    # Run in foreground
    $PYTHON_CMD -c "from neograph.Neo4jProcessor import process_news_data; process_news_data($batch_size, $max_items, True)"
  fi
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
  reset-all)
    # Before running reset, show what we're working with
    log_settings
    
    # Stop all processes first
    echo "Stopping all processes..."
    stop_monitor
    stop
    sleep 2
    
    # Force kill any remaining related processes
    kill_all_related_processes
    
    # Reset Redis databases
    echo "Clearing Redis databases..."
    detect_python
    
    # Use direct Redis commands to clear databases
    echo "Executing Redis reset..."
    if command -v redis-cli >/dev/null 2>&1; then
      redis-cli flushall
      echo "Redis databases cleared successfully"
    else
      echo "Redis CLI not found. Attempting Python fallback..."
      $PYTHON_CMD -c "
from utils.redisClasses import EventTraderRedis, RedisKeys
# Clear news Redis
news_redis = EventTraderRedis(source=RedisKeys.SOURCE_NEWS)
news_redis.clear(preserve_processed=False)
# Clear reports Redis
reports_redis = EventTraderRedis(source=RedisKeys.SOURCE_REPORTS)
reports_redis.clear(preserve_processed=False)
print('Redis databases cleared successfully via Python')
"
    fi
    
    # Reset Neo4j database
    echo "Clearing Neo4j database..."
    # Change to workspace directory first to ensure correct path
    cd "$WORKSPACE_DIR"
    $PYTHON_CMD -c "
from neograph.Neo4jConnection import get_manager
import os
from dotenv import load_dotenv

# Load environment variables - use absolute path to workspace .env
dotenv_path = os.path.abspath('.env')
# Suppress environment loading message
load_dotenv(dotenv_path, verbose=False)

# Use the singleton manager
try:
    neo4j = get_manager()

    # Clear the database
    try:
        neo4j.clear_db()
        print('Database cleared successfully')
    except Exception as e:
        print(f'Error clearing Neo4j database: {e}')
        print('Using direct Cypher query as fallback...')
        # Try direct Cypher query as fallback
        try:
            with neo4j.driver.session() as session:
                session.run('MATCH (n) DETACH DELETE n')
                print('Neo4j database cleared using direct query')
        except Exception as e2:
            print(f'Failed to clear Neo4j database: {e2}')
    # Don't close the singleton manager
except Exception as e:
    print(f'Neo4j connection failed: {e}')
    print('Could not clear Neo4j database')
"
    
    # Wait a moment to ensure Neo4j reset completes fully
    echo "Waiting for Neo4j reset to complete..."
    sleep 5
    
    echo "Reset complete. All databases have been cleared."
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
    
    # Verify everything is really stopped
    sleep 1
    if pgrep -f "python.*run_event_trader.py" > /dev/null 2>&1 || pgrep -f "Neo4jInitializer" > /dev/null 2>&1 || pgrep -f "watchdog.sh" > /dev/null 2>&1; then
      echo "Some processes are still running, performing forced cleanup..."
      kill_all_related_processes
    fi
    ;;
  clean-logs)
    # Clean old log files
    clean_logs
    ;;
  init-neo4j)
    # Initialize Neo4j database
    init_neo4j
    ;;
  process-news)
    # Process news data into Neo4j
    process_news
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
    echo "  reset-all                    # Reset all processes and clear databases"
    echo "  status                       # Show status and recent logs"
    echo "  health                       # Show detailed system health information"
    echo "  logs                         # Show more detailed logs"
    echo "  monitor [max_restarts] [interval]  # Start watchdog"
    echo "  stop-monitor                 # Stop the watchdog"
    echo "  stop-all                     # Stop both watchdog and EventTrader"
    echo "  clean-logs [days]            # Clean log files older than specified days"
    echo "  init-neo4j                   # Initialize Neo4j database"
    echo "  process-news                 # Process news data into Neo4j"
    echo ""
    echo "Options:"
    echo "  --background                 # Run commands in background mode"
    echo "  -historical                  # Enable historical data only (disables live)"
    echo "  -live                        # Enable live data only (disables historical)"
    echo ""
    echo "Examples:"
    echo "  $0 start                        # Start with yesterday to today"
    echo "  $0 start 2025-03-04 2025-03-05  # Start with specific dates" 
    echo "  $0 --background start-all       # Start everything in background"
    echo "  $0 start -historical            # Start with historical data only"
    echo "  $0 start -live                  # Start with live data only"
    echo "  $0 monitor 10 120               # Start watchdog with 10 max restarts, 120s check interval"
    echo "  $0 clean-logs 14                # Clean logs older than 14 days"
    echo "  $0 --background reset-all       # Reset all processes and clear Redis and Neo4j databases"
    exit 1
    ;;
esac

exit 0 