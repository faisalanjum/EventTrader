#!/bin/bash
# Monitor the progress of returns processing

echo "Monitoring returns processing..."
echo "================================"

while true; do
    # Check if process is still running
    if ps aux | grep -q "[p]ython scripts/process_valid_tickers.py"; then
        # Get latest progress
        PROGRESS=$(grep -E "^\[[0-9]+/[0-9]+\] Processing" /home/faisal/EventMarketDB/logs/process_valid_tickers_*.log | tail -1)
        SUCCESS=$(grep -E "success, [0-9]+ failed" /home/faisal/EventMarketDB/logs/process_valid_tickers_*.log | tail -10 | grep -E "[1-9]+ success" | wc -l)
        
        echo -ne "\r$PROGRESS | Tickers processed with success: $SUCCESS"
        
        # Check if finished
        if grep -q "FINAL SUMMARY" /home/faisal/EventMarketDB/logs/process_valid_tickers_*.log; then
            echo -e "\n\nProcessing Complete!"
            grep -A5 "FINAL SUMMARY" /home/faisal/EventMarketDB/logs/process_valid_tickers_*.log
            break
        fi
        
        sleep 5
    else
        echo -e "\n\nProcess not running. Checking if completed..."
        if grep -q "FINAL SUMMARY" /home/faisal/EventMarketDB/logs/process_valid_tickers_*.log; then
            grep -A5 "FINAL SUMMARY" /home/faisal/EventMarketDB/logs/process_valid_tickers_*.log
        else
            echo "Process terminated without completion."
        fi
        break
    fi
done