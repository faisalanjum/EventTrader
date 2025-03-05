#!/bin/bash
# EventTrader Control Script
# Usage: ./scripts/event_trader.sh {start|stop|status|restart|monitor} [from-date] [to-date]

# Configuration
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$WORKSPACE_DIR/event_trader.pid"
LOG_FILE="$WORKSPACE_DIR/logs/event_trader.log"
STATUS_FILE="$WORKSPACE_DIR/event_trader_status.json"
MONITOR_PID_FILE="$WORKSPACE_DIR/event_trader_monitor.pid"

# Default dates (yesterday to today)
FROM_DATE="${2:-$(date -v-1d +%Y-%m-%d)}"
TO_DATE="${3:-$(date +%Y-%m-%d)}"

# Make scripts executable
chmod +x "$WORKSPACE_DIR/scripts/run_event_trader.py" 2>/dev/null

# Ensure log directory exists
mkdir -p "$WORKSPACE_DIR/logs"

# Check if running
is_running() {
  if [ -f "$PID_FILE" ]; then
    pid=$(cat "$PID_FILE")
    if ps -p "$pid" > /dev/null; then
      return 0  # Running
    fi
  fi
  return 1  # Not running
}

# Check if monitor is running
is_monitor_running() {
  if [ -f "$MONITOR_PID_FILE" ]; then
    pid=$(cat "$MONITOR_PID_FILE")
    if ps -p "$pid" > /dev/null; then
      return 0  # Running
    fi
  fi
  return 1  # Not running
}

# Start EventTrader
start() {
  if is_running; then
    echo "EventTrader is already running (PID: $(cat $PID_FILE))"
    return
  fi
  
  echo "Starting EventTrader ($FROM_DATE to $TO_DATE)..."
  cd "$WORKSPACE_DIR"
  
  # Ensure the script is executable
  chmod +x "$WORKSPACE_DIR/scripts/run_event_trader.py"
  
  # Start in background, redirecting output to log
  "$WORKSPACE_DIR/scripts/run_event_trader.py" --from-date "$FROM_DATE" --to-date "$TO_DATE" >> "$LOG_FILE" 2>&1 &
  
  pid=$!
  echo $pid > "$PID_FILE"
  echo "EventTrader started with PID $pid"
  
  # Optional: wait briefly and verify it's still running
  sleep 2
  if ! ps -p $pid > /dev/null; then
    echo "WARNING: Process appears to have terminated immediately. Check logs."
    cat "$LOG_FILE" | tail -n 20
  fi
}

# Stop EventTrader
stop() {
  if ! is_running; then
    echo "EventTrader is not running"
    return
  fi
  
  pid=$(cat "$PID_FILE")
  echo "Stopping EventTrader (PID: $pid)..."
  
  # Send SIGTERM for graceful shutdown
  kill -TERM $pid
  
  # Wait for process to exit
  for i in {1..30}; do
    if ! is_running; then
      echo "EventTrader stopped successfully"
      rm -f "$PID_FILE"
      return
    fi
    echo -n "."
    sleep 1
  done
  echo ""
  
  # If still running after 30 seconds, force kill
  if is_running; then
    echo "Force killing EventTrader process..."
    kill -9 $pid
    rm -f "$PID_FILE"
  fi
}

# Show status
status() {
  if is_running; then
    pid=$(cat "$PID_FILE")
    uptime=$(ps -o etime= -p "$pid" | tr -d ' ')
    echo "EventTrader is running (PID: $pid, Uptime: $uptime)"
    
    # Show monitor status if applicable
    if is_monitor_running; then
      echo "Watchdog monitor is active (PID: $(cat $MONITOR_PID_FILE))"
    else
      echo "Watchdog monitor is not active"
    fi
    
    # Show status from status file if available
    if [ -f "$STATUS_FILE" ]; then
      echo "Status from $STATUS_FILE:"
      cat "$STATUS_FILE" | grep -v timestamp | sed 's/[{}",]//g' | sed 's/:/: /g'
    fi
    
    # Show recent logs
    echo "Recent logs:"
    tail -n 10 "$LOG_FILE"
  else
    echo "EventTrader is not running"
    
    # Show monitor status if applicable
    if is_monitor_running; then
      echo "Watchdog monitor is active (PID: $(cat $MONITOR_PID_FILE))"
    fi
    
    # Check if crashed
    if [ -f "$STATUS_FILE" ] && grep -q "crashed" "$STATUS_FILE"; then
      echo "WARNING: System appears to have crashed."
      echo "Last 20 log entries:"
      tail -n 20 "$LOG_FILE"
    fi
  fi
}

# Monitor mode (optional watchdog)
monitor() {
  if is_monitor_running; then
    echo "Monitor is already running (PID: $(cat $MONITOR_PID_FILE))"
    return
  fi
  
  # Start the monitor in the background
  {
    # Save PID for management
    echo $$ > "$MONITOR_PID_FILE"
    
    # Variables for monitoring
    max_restarts=5
    restart_count=0
    check_interval=60  # Check every minute
  
    echo "$(date): Starting EventTrader monitor (watchdog)..."
    
    # If EventTrader is not running, start it
    if ! is_running; then
      echo "$(date): EventTrader not running. Starting it..."
      start
    fi
    
    # Monitor loop
    while true; do
      # Check if process died
      if ! is_running; then
        if [ $restart_count -lt $max_restarts ]; then
          echo "$(date): EventTrader not running. Attempting restart ($((restart_count+1)) of $max_restarts)"
          start
          restart_count=$((restart_count + 1))
        else
          echo "$(date): Reached maximum restarts ($max_restarts). Manual intervention required."
          rm -f "$MONITOR_PID_FILE"
          exit 1
        fi
      else
        # Reset restart counter if system has been stable for a while
        if [ -f "$PID_FILE" ]; then
          pid=$(cat "$PID_FILE")
          # Check if process has been running for more than 30 minutes
          if ps -p $pid -o etime= | grep -q -E '[0-9]+:[0-9]{2}:[0-9]{2}|[0-9]+-.+'; then
            # Running for hours or days
            restart_count=0
          elif ps -p $pid -o etime= | grep -q -E '([3-9][0-9]|[1-9][0-9]{2,}):[0-9]{2}'; then
            # Running for 30+ minutes
            restart_count=0
          fi
        fi
      fi
      
      sleep $check_interval
    done
  } >> "$WORKSPACE_DIR/logs/event_trader_monitor.log" 2>&1 &
  
  monitor_pid=$!
  echo $monitor_pid > "$MONITOR_PID_FILE"
  echo "Monitor started with PID $monitor_pid"
}

# Stop the monitor
stop_monitor() {
  if ! is_monitor_running; then
    echo "Monitor is not running"
    return
  fi
  
  pid=$(cat "$MONITOR_PID_FILE")
  echo "Stopping monitor (PID: $pid)..."
  kill -TERM $pid
  rm -f "$MONITOR_PID_FILE"
  echo "Monitor stopped"
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
  monitor)
    # Start watchdog mode
    monitor
    ;;
  stop-monitor)
    # Stop the watchdog
    stop_monitor
    ;;
  stop-all)
    # Stop both monitor and main process
    stop_monitor
    stop
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|monitor|stop-monitor|stop-all} [from-date] [to-date]"
    echo "Examples:"
    echo "  $0 start                        # Start with yesterday to today"
    echo "  $0 start 2025-03-04 2025-03-05  # Start with specific dates"
    echo "  $0 monitor                      # Start watchdog mode"
    echo "  $0 stop-all                     # Stop both main process and watchdog"
    exit 1
    ;;
esac

exit 0 