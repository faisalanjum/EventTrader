#!/bin/bash
# MCP server wrapper for Claude CLI - Perplexity (Official)
# Package: @perplexity-ai/mcp-server (https://github.com/perplexityai/modelcontextprotocol)

# Source the .env file to get PERPLEXITY_API_KEY
if [ -f "/home/faisal/EventMarketDB/.env" ]; then
    set -a
    source /home/faisal/EventMarketDB/.env
    set +a
fi

# Verify the API key is set
if [ -z "$PERPLEXITY_API_KEY" ]; then
    echo "ERROR: PERPLEXITY_API_KEY not set" >&2
    exit 1
fi

# Run the official Perplexity MCP server
exec npx -y @perplexity-ai/mcp-server
