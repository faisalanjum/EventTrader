#!/bin/bash
cd /home/faisal/EventMarketDB
source venv/bin/activate
cd drivers/drivers_graph

# Load API key if needed
if [ -z "$LANGSMITH_API_KEY" ]; then
    export $(grep LANGSMITH_API_KEY ../../.env | xargs)
fi

# Fix NEO4J_URI to use correct port
export NEO4J_URI=bolt://192.168.40.74:30687

# Kill any existing langgraph processes first
echo "Checking for existing LangGraph processes..."
if pgrep -f "langgraph dev" > /dev/null; then
    echo "Found existing LangGraph processes. Killing them..."
    pkill -f "langgraph dev"
    sleep 2
fi

# Check if port 2024 is in use
if lsof -i :2024 > /dev/null 2>&1; then
    echo "Port 2024 is still in use. Waiting for it to be released..."
    sleep 3
    if lsof -i :2024 > /dev/null 2>&1; then
        echo "ERROR: Port 2024 is still occupied. Please check for stuck processes."
        echo "Run: lsof -i :2024"
        exit 1
    fi
fi

echo "Starting LangGraph Studio with tunnel..."
echo "========================================="
echo ""

# Temporary file to capture output
TMPFILE=$(mktemp)

# Run in background and capture output
langgraph dev --tunnel > "$TMPFILE" 2>&1 &
PID=$!

# Wait for tunnel URL to appear
echo "Waiting for tunnel URL..."
for i in {1..30}; do
    if grep -q "trycloudflare.com" "$TMPFILE" 2>/dev/null; then
        # Extract the tunnel URL
        URL=$(grep -o 'https://[^[:space:]]*\.trycloudflare\.com' "$TMPFILE" | head -1)
        if [ ! -z "$URL" ]; then
            echo ""
            printf "\033[1;31m"  # Bold red
            echo "========================================="
            echo "COPY THIS URL TO YOUR BROWSER:"
            echo ""
            echo "https://smith.langchain.com/studio/?baseUrl=$URL"
            echo ""
            echo "========================================="
            printf "\033[0m"
            echo ""
            break
        fi
    fi
    sleep 1
done

# Now show the rest of the output
tail -f "$TMPFILE" &
TAIL_PID=$!

# Set up signal handlers to clean up properly
trap "cleanup" INT TERM EXIT

cleanup() {
    echo "\nCleaning up..."
    if [ ! -z "$PID" ]; then
        kill $PID 2>/dev/null
    fi
    if [ ! -z "$TAIL_PID" ]; then
        kill $TAIL_PID 2>/dev/null
    fi
    # Kill any child cloudflared processes
    pkill -P $PID 2>/dev/null
    rm -f "$TMPFILE"
    exit
}

# Wait for the main process
wait $PID

# Clean up
kill $TAIL_PID 2>/dev/null
rm -f "$TMPFILE"