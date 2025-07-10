#!/bin/bash
# Wrapper script to run MCP servers as long-running services

SERVER_TYPE=$1

echo "Starting MCP Server: $SERVER_TYPE"

# Create a named pipe for input
mkfifo /tmp/mcp_input

# Function to keep the pipe open
keep_pipe_open() {
    while true; do
        sleep 3600
    done > /tmp/mcp_input
}

# Start the pipe keeper in background
keep_pipe_open &
PIPE_PID=$!

# Trap to clean up on exit
trap "kill $PIPE_PID; rm -f /tmp/mcp_input" EXIT

# Run the MCP server with the pipe as input
if [ "$SERVER_TYPE" = "cypher" ]; then
    exec python /app/mcp_servers/neo4j_cypher_server.py < /tmp/mcp_input
elif [ "$SERVER_TYPE" = "memory" ]; then
    exec python /app/mcp_servers/neo4j_memory_server.py < /tmp/mcp_input
else
    echo "Unknown server type: $SERVER_TYPE"
    exit 1
fi