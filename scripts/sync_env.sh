#!/bin/bash
# Production-grade script to synchronize .env file across all nodes
# Requires SSH keys to be set up between nodes

set -e  # Exit on error

# Configuration
NODES=(
    "faisal@192.168.40.72:/home/faisal/EventMarketDB/.env"  # minisforum2
    "faisal@192.168.40.74:/home/faisal/EventMarketDB/.env"  # minisforum3
)
SOURCE_FILE="/home/faisal/EventMarketDB/.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}EventMarketDB .env File Synchronization${NC}"
echo "========================================"

# Verify source file exists
if [ ! -f "$SOURCE_FILE" ]; then
    echo -e "${RED}ERROR: Source .env file not found at $SOURCE_FILE${NC}"
    exit 1
fi

# Show key configuration values
echo -e "\n${GREEN}Current Configuration:${NC}"
echo "NEO4J_URI:    $(grep NEO4J_URI "$SOURCE_FILE" | cut -d= -f2)"
echo "REDIS_HOST:   $(grep REDIS_HOST "$SOURCE_FILE" | cut -d= -f2)"
echo "REDIS_PORT:   $(grep REDIS_PORT "$SOURCE_FILE" | cut -d= -f2)"

# Sync to each node
echo -e "\n${YELLOW}Syncing to nodes...${NC}"
for target in "${NODES[@]}"; do
    echo -n "→ Copying to $target... "
    
    if scp -q -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$SOURCE_FILE" "$target" 2>/dev/null; then
        echo -e "${GREEN}✓ Success${NC}"
    else
        echo -e "${RED}✗ Failed${NC}"
        echo "  Hint: Ensure SSH keys are set up: ssh-copy-id ${target%%:*}"
    fi
done

echo -e "\n${GREEN}Sync complete!${NC}"
echo ""
echo "To verify on each node, run:"
echo "  grep -E 'NEO4J_URI|REDIS_HOST' /home/faisal/EventMarketDB/.env"