#!/bin/bash
# EventTrader Watchdog
# This script monitors the EventTrader system and restarts it if it crashes
# Usage: ./scripts/watchdog.sh [max_restarts] [check_interval]

# Get workspace directory
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTROL_SCRIPT="$WORKSPACE_DIR/scripts/event_trader.sh"
PID_FILE="$WORKSPACE_DIR/event_trader.pid"
STATUS_FILE="$WORKSPACE_DIR/event_trader_status.json"
LOG_FILE="$WORKSPACE_DIR/logs/watchdog.log"

# Parameters
MAX_RESTARTS=${1:-5}  # Default to 5 restart attempts
CHECK_INTERVAL=${2:-60}  # Default to checking every 60 seconds (1 minute)

# Ensure log directory exists
mkdir -p "$WORKSPACE_DIR/logs"

# Log with timestamp
log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Check if EventTrader is running
is_running() {
  if [ -f "$PID_FILE" ]; then
    pid=$(cat "$PID_FILE")
    if ps -p "$pid" > /dev/null; then
      return 0  # Running
    fi
  fi
  return 1  # Not running
}

# Main watchdog function
watchdog() {
  log "Starting EventTrader Watchdog (Max restarts: $MAX_RESTARTS, Check interval: ${CHECK_INTERVAL}s)"
  
  # Initialize counters
  restart_count=0
  consecutive_stable_checks=0
  
  # If EventTrader is not running, start it
  if ! is_running; then
    log "EventTrader not running. Starting it..."
    $CONTROL_SCRIPT start
  else
    log "EventTrader already running (PID: $(cat $PID_FILE))"
  fi
  
  # Monitoring loop
  while true; do
    # Check if process is running
    if ! is_running; then
      # Check if it crashed according to status file
      if [ -f "$STATUS_FILE" ] && (grep -q "crashed" "$STATUS_FILE" || grep -q "starting" "$STATUS_FILE"); then
        log "EventTrader is not running or crashed"
        
        if [ $restart_count -lt $MAX_RESTARTS ]; then
          restart_count=$((restart_count + 1))
          log "Attempting restart $restart_count of $MAX_RESTARTS"
          $CONTROL_SCRIPT start
          
          # Give it a moment to start
          sleep 5
          
          # Verify it started
          if ! is_running; then
            log "Failed to restart EventTrader"
          else
            log "EventTrader restarted successfully"
          fi
        else
          log "ERROR: Maximum restart attempts ($MAX_RESTARTS) reached. Manual intervention required."
          log "Check the EventTrader logs for details about the crashes."
          exit 1
        fi
      fi
    else
      # Process is running, check how long it's been running
      pid=$(cat "$PID_FILE")
      uptime=$(ps -o etime= -p "$pid" | tr -d ' ')
      log "EventTrader running (PID: $pid, Uptime: $uptime)"
      
      # If running for more than 30 minutes consecutively, reset restart counter
      if [[ "$uptime" == *":"*":"* ]] || [[ "$uptime" == *"-"* ]]; then
        # Format is HH:MM:SS or DD-HH:MM
        consecutive_stable_checks=$((consecutive_stable_checks + 1))
        
        if [ $consecutive_stable_checks -ge 5 ]; then
          # Reset counter after 5 consecutive stable checks
          if [ $restart_count -gt 0 ]; then
            log "System has been stable for a while, resetting restart counter"
            restart_count=0
          fi
        fi
      elif [[ "$uptime" == *":"* ]]; then
        # Format is MM:SS
        minutes=${uptime%:*}
        if [ $minutes -ge 30 ]; then
          consecutive_stable_checks=$((consecutive_stable_checks + 1))
          
          if [ $consecutive_stable_checks -ge 5 ]; then
            # Reset counter after 5 consecutive stable checks
            if [ $restart_count -gt 0 ]; then
              log "System has been stable for a while, resetting restart counter"
              restart_count=0
            fi
          fi
        fi
      fi
    fi
    
    # Wait for next check
    sleep $CHECK_INTERVAL
  done
}

# Run the watchdog
watchdog 