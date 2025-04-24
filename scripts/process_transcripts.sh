#!/bin/bash

# Script to process transcripts through Neo4jProcessor.py
# Usage: ./process_transcripts.sh [--batch N] [--max N] [--skip-without-returns]

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (one level up from script directory)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Set PYTHONPATH to include the project root
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Function to extract credentials from various sources
get_neo4j_credentials() {
    local found_credentials=false
    echo "Searching for Neo4j credentials..."
    
    # Try to get credentials from .env file first
    if [ -f "$PROJECT_ROOT/.env" ]; then
        echo "Found .env file, checking for Neo4j credentials..."
        
        # Look for NEO4J_USERNAME and NEO4J_PASSWORD (handle both with and without = sign)
        NEO4J_USER_ENV=$(grep -E '^NEO4J_USERNAME|^NEO4J_USER' "$PROJECT_ROOT/.env" | sed -E 's/^NEO4J_USERNAME=?|^NEO4J_USER=?//' | tr -d '"' | tr -d "'")
        NEO4J_PASSWORD_ENV=$(grep -E '^NEO4J_PASSWORD' "$PROJECT_ROOT/.env" | sed -E 's/^NEO4J_PASSWORD=?//' | tr -d '"' | tr -d "'")
        
        # Also look for non-standard formats without equals signs
        if [ -z "$NEO4J_USER_ENV" ]; then
            NEO4J_USER_ENV=$(grep -E '^NEO4J_USERNAME|^NEO4J_USER' "$PROJECT_ROOT/.env" | sed -E 's/^NEO4J_USERNAME|^NEO4J_USER//' | tr -d '"' | tr -d "'")
        fi
        
        if [ -z "$NEO4J_PASSWORD_ENV" ]; then
            NEO4J_PASSWORD_ENV=$(grep -E '^NEO4J_PASSWORD' "$PROJECT_ROOT/.env" | sed -E 's/^NEO4J_PASSWORD//' | tr -d '"' | tr -d "'")
        fi
        
        if [ -n "$NEO4J_USER_ENV" ] && [ -n "$NEO4J_PASSWORD_ENV" ]; then
            NEO4J_USER="$NEO4J_USER_ENV"
            NEO4J_PASSWORD="$NEO4J_PASSWORD_ENV"
            echo "Found Neo4j credentials in .env file: user=$NEO4J_USER, password=***"
            found_credentials=true
        fi
        
        # Direct detection of credentials without any formatting - hardcoded for your specific format
        if [ "$found_credentials" = false ]; then
            # Handle the specific format in your .env file: NEO4J_USERNAME=neo4jNEO4J_PASSWORD=Next2020
            SPECIFIC_USER=$(grep -o 'NEO4J_USERNAME=[a-zA-Z0-9]*' "$PROJECT_ROOT/.env" | sed 's/NEO4J_USERNAME=//')
            SPECIFIC_PASSWORD=$(grep -o 'NEO4J_PASSWORD=[a-zA-Z0-9]*' "$PROJECT_ROOT/.env" | sed 's/NEO4J_PASSWORD=//')
            
            if [ -n "$SPECIFIC_USER" ] && [ -n "$SPECIFIC_PASSWORD" ]; then
                NEO4J_USER="$SPECIFIC_USER"
                NEO4J_PASSWORD="$SPECIFIC_PASSWORD"
                echo "Found Neo4j credentials in .env file (specific format): user=$NEO4J_USER, password=***"
                found_credentials=true
            fi
        fi
    fi
    
    # Hard-coded fallback if all else fails
    if [ "$found_credentials" = false ]; then
        echo "Using hardcoded fallback credentials"
        NEO4J_USER="neo4j"
        NEO4J_PASSWORD="Next2020#"
        found_credentials=true
    fi
    
    # Final fallback to defaults
    if [ "$found_credentials" = false ]; then
        echo "No Neo4j credentials found, using defaults (neo4j/neo4j)"
        NEO4J_USER="neo4j"
        NEO4J_PASSWORD="neo4j"
    fi
    
    # Export the credentials as environment variables for the Python script
    export NEO4J_USERNAME="$NEO4J_USER"
    export NEO4J_PASSWORD="$NEO4J_PASSWORD"
}

# Get Neo4j credentials
get_neo4j_credentials

# Default to verbose mode
VERBOSE="--verbose"

# Parse custom options
OPTIONS=""
for arg in "$@"; do
    OPTIONS="$OPTIONS $arg"
done

echo "Starting transcript processing..."
echo "Using Neo4j credentials - Username: $NEO4J_USER, Password: (hidden)"
echo "Full command: python $PROJECT_ROOT/neograph/Neo4jProcessor.py transcripts $OPTIONS $VERBOSE"

# Run the Neo4jProcessor script in transcripts mode with all arguments passed to this script
python "$PROJECT_ROOT/neograph/Neo4jProcessor.py" transcripts $OPTIONS $VERBOSE

echo "Transcript processing completed." 