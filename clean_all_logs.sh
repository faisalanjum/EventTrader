#!/bin/bash
# Script to clean logs on all nodes

echo "Cleaning logs on all nodes..."

# Clean local logs (minisforum)
echo "Cleaning logs on minisforum (local)..."
sudo rm -rf /home/faisal/EventMarketDB/logs/*.log
sudo rm -rf /home/faisal/EventMarketDB/logs/ChunkHist_*
sudo rm -rf /home/faisal/EventMarketDB/logs/backup_*

# For minisforum2 and minisforum3, we need to use kubectl debug or ssh with proper keys
echo ""
echo "To clean logs on minisforum2 (192.168.40.72) and minisforum3 (192.168.40.74),"
echo "you need to manually SSH to each node and run:"
echo ""
echo "sudo rm -rf /home/faisal/EventMarketDB/logs/*.log"
echo "sudo rm -rf /home/faisal/EventMarketDB/logs/ChunkHist_*"
echo "sudo rm -rf /home/faisal/EventMarketDB/logs/backup_*"
echo ""
echo "Or use these commands with proper SSH access:"
echo "ssh faisal@192.168.40.72 'sudo rm -rf /home/faisal/EventMarketDB/logs/*.log /home/faisal/EventMarketDB/logs/ChunkHist_* /home/faisal/EventMarketDB/logs/backup_*'"
echo "ssh faisal@192.168.40.74 'sudo rm -rf /home/faisal/EventMarketDB/logs/*.log /home/faisal/EventMarketDB/logs/ChunkHist_* /home/faisal/EventMarketDB/logs/backup_*'"

# List remaining files
echo ""
echo "Remaining files on minisforum:"
ls -la /home/faisal/EventMarketDB/logs/