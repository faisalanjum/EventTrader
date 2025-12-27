#!/bin/bash

# Auto Transcript Cleaner Script - ROBUST VERSION
# This script monitors chunk processing and removes duplicate transcripts from Redis
# that already exist in Neo4j with complete INFLUENCES relationships

LOG_DIR="/home/faisal/EventMarketDB/logs/ChunkHist_2025-04-30_to_2025-05-19_20250725_003835"
STATS_FILE="/tmp/transcript_cleanup_stats.csv"
LOG_FILE="/tmp/transcript_cleanup.log"
NEO4J_USER="neo4j"
NEO4J_PASS="Next2020#"

# Configuration
MAX_WAIT_FOR_COMPLETION=7200  # 2 hours max wait for chunk completion
END_DATE_PATTERN="2025-07-22"  # Actual end date
TICKER_COUNT_PATTERN="Tickers Processed: [0-9]"  # Flexible ticker count

# Initialize stats file
echo "Timestamp,Chunk,Transcripts_Checked,Transcripts_Deleted" > $STATS_FILE

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

# Get pod names with retry
get_pod_names() {
    local retries=5
    while [ $retries -gt 0 ]; do
        REDIS_POD=$(kubectl get pods -n infrastructure -l app=redis -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        NEO4J_POD=$(kubectl get pods -n neo4j -l app=neo4j -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        
        if [ -n "$REDIS_POD" ] && [ -n "$NEO4J_POD" ]; then
            return 0
        fi
        
        log "WARNING: Failed to get pod names, retrying... ($retries attempts left)"
        sleep 10
        ((retries--))
    done
    
    log "ERROR: Failed to get pod names after multiple attempts"
    return 1
}

check_transcript_fully_processed() {
    local transcript_id="$1"
    
    # Skip empty transcript IDs
    if [ -z "$transcript_id" ] || [ "$transcript_id" = " " ]; then
        echo "0"
        return
    fi
    
    # Escape single quotes in transcript ID
    local escaped_id="${transcript_id//\'/\'\'}"
    
    # Check if transcript exists in Neo4j with all INFLUENCES relationships having proper values
    local check_query="
    MATCH (t:Transcript {id: '$escaped_id'})
    OPTIONAL MATCH (t)-[ic:INFLUENCES]->(c:Company)
    OPTIONAL MATCH (t)-[ii:INFLUENCES]->(i:Industry)
    OPTIONAL MATCH (t)-[is:INFLUENCES]->(s:Sector)
    OPTIONAL MATCH (t)-[im:INFLUENCES]->(m:MarketIndex)
    WITH t,
         CASE WHEN ic IS NOT NULL 
              AND ic.daily_stock IS NOT NULL AND ic.hourly_stock IS NOT NULL AND ic.session_stock IS NOT NULL
              AND ic.daily_industry IS NOT NULL AND ic.hourly_industry IS NOT NULL AND ic.session_industry IS NOT NULL
              AND ic.daily_sector IS NOT NULL AND ic.hourly_sector IS NOT NULL AND ic.session_sector IS NOT NULL
              AND ic.daily_macro IS NOT NULL AND ic.hourly_macro IS NOT NULL AND ic.session_macro IS NOT NULL
              THEN 1 ELSE 0 END as company_complete,
         CASE WHEN ii IS NOT NULL 
              AND ii.daily_industry IS NOT NULL AND ii.hourly_industry IS NOT NULL AND ii.session_industry IS NOT NULL
              THEN 1 ELSE 0 END as industry_complete,
         CASE WHEN is IS NOT NULL 
              AND is.daily_sector IS NOT NULL AND is.hourly_sector IS NOT NULL AND is.session_sector IS NOT NULL
              THEN 1 ELSE 0 END as sector_complete,
         CASE WHEN im IS NOT NULL 
              AND im.daily_macro IS NOT NULL AND im.hourly_macro IS NOT NULL AND im.session_macro IS NOT NULL
              THEN 1 ELSE 0 END as market_complete
    RETURN CASE WHEN t IS NOT NULL 
                AND company_complete = 1 
                AND industry_complete = 1 
                AND sector_complete = 1 
                AND market_complete = 1 
           THEN 1 ELSE 0 END as fully_processed"
    
    # Get current pod name in case it changed
    get_pod_names || return
    
    local result=$(kubectl exec $NEO4J_POD -n neo4j -- cypher-shell -u $NEO4J_USER -p "$NEO4J_PASS" \
        "$check_query" --format plain 2>/dev/null | grep -E '^[0-1]$' | head -1)
    
    # Default to 0 if query fails
    echo "${result:-0}"
}

clean_transcripts_for_chunk() {
    local chunk_name="$1"
    log "Cleaning transcripts for chunk: $chunk_name"
    
    # Get current pod name in case it changed
    get_pod_names || return
    
    # Get all transcript IDs from Redis
    kubectl exec $REDIS_POD -n infrastructure -- redis-cli KEYS "transcripts:hist:raw:*" 2>/dev/null | sort > /tmp/transcript_ids_${chunk_name}.txt
    
    # Check if file was created and has content
    if [ ! -s /tmp/transcript_ids_${chunk_name}.txt ]; then
        log "No transcripts found in Redis or Redis command failed"
        return
    fi
    
    local total=$(wc -l < /tmp/transcript_ids_${chunk_name}.txt)
    log "Found $total transcripts in Redis to check"
    
    local deleted=0
    local checked=0
    
    while IFS= read -r redis_key; do
        # Skip empty lines
        [ -z "$redis_key" ] && continue
        
        ((checked++))
        transcript_id="${redis_key#transcripts:hist:raw:}"
        
        # Skip if transcript_id is empty
        if [ -z "$transcript_id" ]; then
            log "WARNING: Empty transcript ID from key: $redis_key"
            continue
        fi
        
        # Check if fully processed with all INFLUENCES relationships
        local fully_processed=$(check_transcript_fully_processed "$transcript_id")
        
        if [ "$fully_processed" = "1" ]; then
            log "[$checked/$total] Transcript $transcript_id is FULLY processed, deleting from Redis..."
            kubectl exec $REDIS_POD -n infrastructure -- redis-cli DEL "$redis_key" >/dev/null 2>&1
            ((deleted++))
        else
            log "[$checked/$total] Transcript $transcript_id is NOT fully processed, keeping in Redis"
        fi
        
        # Progress update every 10 transcripts
        if [ $((checked % 10)) -eq 0 ]; then
            log "Progress: $checked/$total checked, $deleted deleted so far"
        fi
    done < /tmp/transcript_ids_${chunk_name}.txt
    
    # Log stats
    echo "$(date '+%Y-%m-%d %H:%M:%S'),$chunk_name,$checked,$deleted" >> $STATS_FILE
    log "Completed cleaning for chunk $chunk_name: $deleted/$checked transcripts deleted"
    
    # Cleanup temp file
    rm -f /tmp/transcript_ids_${chunk_name}.txt
}

monitor_chunk() {
    local chunk_file="$1"
    local chunk_name=$(basename "$chunk_file" .log)
    
    log "Monitoring chunk: $chunk_name"
    
    # First wait for tickers to be processed (flexible count)
    local ticker_wait_count=0
    while true; do
        if grep -q "$TICKER_COUNT_PATTERN" "$chunk_file" 2>/dev/null; then
            local ticker_count=$(grep "$TICKER_COUNT_PATTERN" "$chunk_file" | tail -1 | grep -o "[0-9]*$")
            log "Tickers processed in $chunk_name (count: $ticker_count), now monitoring for transcript blocking..."
            break
        fi
        
        # Check if chunk already completed
        if grep -q "Historical chunk processing finished" "$chunk_file" 2>/dev/null; then
            log "Chunk $chunk_name already completed (found during ticker wait)"
            return
        fi
        
        sleep 30
        ((ticker_wait_count+=30))
        
        # Timeout after 30 minutes
        if [ $ticker_wait_count -gt 1800 ]; then
            log "WARNING: Timeout waiting for tickers to be processed in $chunk_name"
            return
        fi
    done
    
    # Wait for transcripts to block processing
    local transcript_wait_count=0
    while true; do
        if grep -q "transcripts': 'Historical Raw Items Not Empty'" "$chunk_file" 2>/dev/null; then
            log "Transcripts blocking detected in $chunk_name"
            
            # Clean transcripts
            clean_transcripts_for_chunk "$chunk_name"
            
            # Wait for chunk to complete
            log "Waiting for chunk to complete..."
            local completion_wait_count=0
            while ! grep -q "Historical chunk processing finished" "$chunk_file" 2>/dev/null; do
                sleep 30
                ((completion_wait_count+=30))
                
                if [ $completion_wait_count -gt $MAX_WAIT_FOR_COMPLETION ]; then
                    log "ERROR: Timeout waiting for chunk completion after ${MAX_WAIT_FOR_COMPLETION}s"
                    return
                fi
            done
            
            # Wait additional time for cleanup and transition
            log "Chunk processing finished signal detected. Waiting 2 minutes for cleanup..."
            sleep 120
            
            log "Chunk $chunk_name completed!"
            break
        fi
        
        # Check if chunk already completed
        if grep -q "Historical chunk processing finished" "$chunk_file" 2>/dev/null; then
            log "Chunk $chunk_name already completed"
            break
        fi
        
        sleep 60
        ((transcript_wait_count+=60))
        
        # Timeout after 1 hour of no transcript blocking
        if [ $transcript_wait_count -gt 3600 ]; then
            log "WARNING: No transcript blocking detected after 1 hour for $chunk_name, checking if completed"
            if grep -q "Historical chunk processing finished" "$chunk_file" 2>/dev/null; then
                log "Chunk $chunk_name completed without transcript blocking"
            else
                log "WARNING: Chunk $chunk_name neither blocked nor completed, skipping"
            fi
            break
        fi
    done
}

# Main execution
log "=== Starting Auto Transcript Cleaner (ROBUST VERSION) ==="
log "Monitoring directory: $LOG_DIR"
log "End date pattern: $END_DATE_PATTERN"

# Initial pod name check
if ! get_pod_names; then
    log "FATAL: Cannot get pod names, exiting"
    exit 1
fi

# Find all chunk log files
chunk_files=($(ls -1 "$LOG_DIR"/chunk_*.log 2>/dev/null | sort))

if [ ${#chunk_files[@]} -eq 0 ]; then
    log "No chunk files found in $LOG_DIR"
    exit 1
fi

log "Found ${#chunk_files[@]} chunk files"

# Find the latest incomplete chunk
latest_chunk_index=0
for ((i=${#chunk_files[@]}-1; i>=0; i--)); do
    if ! grep -q "Historical chunk processing finished" "${chunk_files[$i]}" 2>/dev/null; then
        latest_chunk_index=$i
        break
    fi
done

# Monitor from the latest chunk onwards
for ((i=$latest_chunk_index; i<${#chunk_files[@]}; i++)); do
    monitor_chunk "${chunk_files[$i]}"
done

# Continue monitoring for new chunks
log "Monitoring for new chunks..."

while true; do
    # Refresh pod names periodically
    get_pod_names || log "WARNING: Failed to refresh pod names"
    
    # Check for new chunk files every 30 seconds
    new_chunks=($(ls -1 "$LOG_DIR"/chunk_*.log 2>/dev/null | sort))
    
    if [ ${#new_chunks[@]} -gt ${#chunk_files[@]} ]; then
        log "New chunk detected!"
        for ((i=${#chunk_files[@]}; i<${#new_chunks[@]}; i++)); do
            monitor_chunk "${new_chunks[$i]}"
        done
        chunk_files=("${new_chunks[@]}")
    fi
    
    # Check if we've reached the end date (corrected pattern)
    if ls "$LOG_DIR"/chunk_*${END_DATE_PATTERN}*.log >/dev/null 2>&1; then
        if grep -q "Historical chunk processing finished" "$LOG_DIR"/chunk_*${END_DATE_PATTERN}*.log 2>/dev/null; then
            log "Reached end date ($END_DATE_PATTERN), processing complete!"
            break
        fi
    fi
    
    sleep 30
done

log "=== Transcript cleaner completed ==="
log "Results saved to: $STATS_FILE"

# Final summary
echo ""
echo "=== FINAL SUMMARY ==="
cat "$STATS_FILE" | column -t -s,