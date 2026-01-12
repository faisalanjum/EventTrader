#!/bin/bash
# Get the current ngrok public URL for MCP server
# Usage: ./mcp-ngrok-url.sh

NGROK_API="http://127.0.0.1:4040/api/tunnels"

# Check if ngrok is running
if ! curl -s "$NGROK_API" > /dev/null 2>&1; then
    echo "ERROR: ngrok is not running or API not accessible" >&2
    exit 1
fi

# Get the public URL
URL=$(curl -s "$NGROK_API" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    tunnels = data.get('tunnels', [])
    if tunnels:
        print(tunnels[0]['public_url'])
    else:
        print('ERROR: No tunnels found', file=sys.stderr)
        sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
")

if [ -z "$URL" ]; then
    echo "ERROR: Could not get ngrok URL" >&2
    exit 1
fi

echo ""
echo "=========================================="
echo "  MCP Server Public URL"
echo "=========================================="
echo ""
echo "For Claude.ai Settings > Connectors:"
echo ""
echo "  Name: Neo4j MCP"
echo "  URL:  ${URL}/mcp"
echo ""
echo "=========================================="
echo ""
