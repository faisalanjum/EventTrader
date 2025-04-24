#!/bin/bash
# neo4j_terminal_report.sh - Comprehensive yet concise Neo4j database structure report
# For terminal display - hierarchical and intuitive visualization

# Get the workspace directory
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WORKSPACE_DIR"

# Setup output files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORTS_DIR="$WORKSPACE_DIR/logs/neo4j_reports"
HTML_FILE="$REPORTS_DIR/neo4j_report_$TIMESTAMP.html"

# Create reports directory if it doesn't exist
mkdir -p "$REPORTS_DIR"

# Function to log output to both terminal and HTML file
log_output() {
    echo -e "$1"
    # Convert ANSI color codes to HTML for the HTML file
    echo -e "$1" | sed -E 's/\x1B\[([0-9]{1,2}(;[0-9]{1,2})?)?[mGK]//g' >> "$HTML_FILE"
}

# Add HTML header with better styling
cat > "$HTML_FILE" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Neo4j Database Report - $TIMESTAMP</title>
    <style>
        body { font-family: monospace; background-color: #1e1e1e; color: #d4d4d4; padding: 20px; max-width: 1200px; margin: 0 auto; }
        h1, h2 { color: #569cd6; }
        .node { color: #4ec9b0; }
        .property { color: #9cdcfe; }
        .relationship { color: #ce9178; }
        .good { color: #6a9955; }
        .warning { color: #d7ba7d; }
        .error { color: #f44747; }
        pre { white-space: pre-wrap; line-height: 1.5; }
        .timestamp { color: #888; font-style: italic; }
    </style>
</head>
<body>
<h1>Neo4j Database Structure Report</h1>
<p class="timestamp">Generated: $(date +"%Y-%m-%d %H:%M")</p>
<pre>
EOF

# Function to extract credentials from various sources
get_neo4j_credentials() {
    local found_credentials=false
    echo "Searching for Neo4j credentials..."
    
    # Try to get credentials from .env file first
    if [ -f "$WORKSPACE_DIR/.env" ]; then
        echo "Found .env file, checking for Neo4j credentials..."
        
        # Look for NEO4J_USERNAME and NEO4J_PASSWORD (handle both with and without = sign)
        NEO4J_USER_ENV=$(grep -E '^NEO4J_USERNAME|^NEO4J_USER' "$WORKSPACE_DIR/.env" | sed -E 's/^NEO4J_USERNAME=?|^NEO4J_USER=?//' | tr -d '"' | tr -d "'")
        NEO4J_PASSWORD_ENV=$(grep -E '^NEO4J_PASSWORD' "$WORKSPACE_DIR/.env" | sed -E 's/^NEO4J_PASSWORD=?//' | tr -d '"' | tr -d "'")
        
        # Also look for non-standard formats without equals signs
        if [ -z "$NEO4J_USER_ENV" ]; then
            NEO4J_USER_ENV=$(grep -E '^NEO4J_USERNAME|^NEO4J_USER' "$WORKSPACE_DIR/.env" | sed -E 's/^NEO4J_USERNAME|^NEO4J_USER//' | tr -d '"' | tr -d "'")
        fi
        
        if [ -z "$NEO4J_PASSWORD_ENV" ]; then
            NEO4J_PASSWORD_ENV=$(grep -E '^NEO4J_PASSWORD' "$WORKSPACE_DIR/.env" | sed -E 's/^NEO4J_PASSWORD//' | tr -d '"' | tr -d "'")
        fi
        
        if [ -n "$NEO4J_USER_ENV" ] && [ -n "$NEO4J_PASSWORD_ENV" ]; then
            NEO4J_USER="$NEO4J_USER_ENV"
            NEO4J_PASSWORD="$NEO4J_PASSWORD_ENV"
            echo "Found Neo4j credentials in .env file: user=$NEO4J_USER, password=***"
            found_credentials=true
        fi
        
        # Try to find URL and extract credentials if available and not already found
        if [ "$found_credentials" = false ]; then
            NEO4J_URI_ENV=$(grep -E '^NEO4J_URI|^NEO4J_URL' "$WORKSPACE_DIR/.env" | sed -E 's/^NEO4J_URI=?|^NEO4J_URL=?//' | tr -d '"' | tr -d "'")
            
            # Also check for format without equals sign
            if [ -z "$NEO4J_URI_ENV" ]; then
                NEO4J_URI_ENV=$(grep -E '^NEO4J_URI|^NEO4J_URL' "$WORKSPACE_DIR/.env" | sed -E 's/^NEO4J_URI|^NEO4J_URL//' | tr -d '"' | tr -d "'")
            fi
            
            if [[ "$NEO4J_URI_ENV" == *"://"*":"*"@"* ]]; then
                echo "Found Neo4j URI with credentials, extracting..."
                NEO4J_USER=$(echo "$NEO4J_URI_ENV" | sed -n 's/.*:\/\/\([^:]*\):\([^@]*\)@.*/\1/p')
                NEO4J_PASSWORD=$(echo "$NEO4J_URI_ENV" | sed -n 's/.*:\/\/\([^:]*\):\([^@]*\)@.*/\2/p')
                if [ -n "$NEO4J_USER" ] && [ -n "$NEO4J_PASSWORD" ]; then
                    echo "Extracted Neo4j credentials from URI: user=$NEO4J_USER, password=***"
                    found_credentials=true
                fi
            fi
        fi
        
        # Direct detection of credentials without any formatting - hardcoded for your specific format
        if [ "$found_credentials" = false ]; then
            # Handle the specific format in your .env file: NEO4J_USERNAME=neo4jNEO4J_PASSWORD=Next2020
            SPECIFIC_USER=$(grep -o 'NEO4J_USERNAME=[a-zA-Z0-9]*' "$WORKSPACE_DIR/.env" | sed 's/NEO4J_USERNAME=//')
            SPECIFIC_PASSWORD=$(grep -o 'NEO4J_PASSWORD=[a-zA-Z0-9]*' "$WORKSPACE_DIR/.env" | sed 's/NEO4J_PASSWORD=//')
            
            if [ -n "$SPECIFIC_USER" ] && [ -n "$SPECIFIC_PASSWORD" ]; then
                NEO4J_USER="$SPECIFIC_USER"
                NEO4J_PASSWORD="$SPECIFIC_PASSWORD"
                echo "Found Neo4j credentials in .env file (specific format): user=$NEO4J_USER, password=***"
                found_credentials=true
            fi
        fi
    fi
    
    # Try to extract credentials from Python files if not found yet
    if [ "$found_credentials" = false ]; then
        echo "Searching Python files for Neo4j credentials..."
        
        # Check neograph/Neo4jConnection.py if it exists
        if [ -f "$WORKSPACE_DIR/neograph/Neo4jConnection.py" ]; then
            echo "Found Neo4jConnection.py, checking for credentials..."
            
            # Try to extract username and password
            NEO4J_USER_PY=$(grep -E "username\s*=|user\s*=" "$WORKSPACE_DIR/neograph/Neo4jConnection.py" | grep -v "os.getenv" | head -1 | sed -n "s/.*[username|user]\s*=\s*[\"']\([^\"']*\)[\"'].*/\1/p")
            NEO4J_PASSWORD_PY=$(grep -E "password\s*=" "$WORKSPACE_DIR/neograph/Neo4jConnection.py" | grep -v "os.getenv" | head -1 | sed -n "s/.*password\s*=\s*[\"']\([^\"']*\)[\"'].*/\1/p")
            
            if [ -n "$NEO4J_USER_PY" ] && [ -n "$NEO4J_PASSWORD_PY" ]; then
                NEO4J_USER="$NEO4J_USER_PY"
                NEO4J_PASSWORD="$NEO4J_PASSWORD_PY"
                echo "Found Neo4j credentials in Neo4jConnection.py: user=$NEO4J_USER, password=***"
                found_credentials=true
            fi
        fi
        
        # Try to use Python to extract credentials
        if [ "$found_credentials" = false ] && command -v python3 >/dev/null 2>&1; then
            echo "Using Python to extract Neo4j credentials from configuration..."
            NEO4J_CREDS=$(python3 -c "
try:
    import os, sys
    sys.path.append('$WORKSPACE_DIR')
    from dotenv import load_dotenv
    load_dotenv('$WORKSPACE_DIR/.env')
    
    # Try to import Neo4j connection module
    try:
        from neograph.Neo4jConnection import get_manager
        neo4j = get_manager()
        if hasattr(neo4j, 'auth') and neo4j.auth:
            print(f'{neo4j.auth[0]} {neo4j.auth[1]}')
        elif hasattr(neo4j, 'username') and hasattr(neo4j, 'password'):
            print(f'{neo4j.username} {neo4j.password}')
    except Exception as e:
        # Try from config files
        try:
            import config.neo4j_config as neo4j_config
            if hasattr(neo4j_config, 'USERNAME') and hasattr(neo4j_config, 'PASSWORD'):
                print(f'{neo4j_config.USERNAME} {neo4j_config.PASSWORD}')
        except:
            pass
except Exception as e:
    pass
" 2>/dev/null)
            
            if [ -n "$NEO4J_CREDS" ]; then
                NEO4J_USER=$(echo "$NEO4J_CREDS" | cut -d' ' -f1)
                NEO4J_PASSWORD=$(echo "$NEO4J_CREDS" | cut -d' ' -f2)
                echo "Extracted Neo4j credentials using Python: user=$NEO4J_USER, password=***"
                found_credentials=true
            fi
        fi
    fi
    
    # Use environment variables as fallback if directly provided to the script
    if [ "$found_credentials" = false ] && [ -n "$NEO4J_USER" ] && [ -n "$NEO4J_PASSWORD" ]; then
        echo "Using Neo4j credentials from environment variables: user=$NEO4J_USER, password=***"
        found_credentials=true
    fi
    
    # Hard-coded fallback for your specific values, if all else fails
    if [ "$found_credentials" = false ]; then
        echo "Using hardcoded fallback credentials from your .env format"
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
}

# Get Neo4j credentials
get_neo4j_credentials

# Display confirmed credentials
log_output "Using Neo4j credentials - Username: $NEO4J_USER, Password: (hidden)"

# Test Neo4j connection before proceeding
log_output "Testing Neo4j connection..."
CONNECTION_TEST=$(cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" --format plain "RETURN 1 as test" 2>&1)
if [[ "$CONNECTION_TEST" == *"Failure to establish connection"* ]] || [[ "$CONNECTION_TEST" == *"unauthorized"* ]]; then
    log_output "ERROR: Could not connect to Neo4j database. Please check credentials and Neo4j status."
    log_output "Connection error: $CONNECTION_TEST"
    log_output ""
    log_output "You can manually specify credentials with:"
    log_output "NEO4J_USER=neo4j NEO4J_PASSWORD='Next2020#' $0"
    
    # Close HTML file
    echo "</pre></body></html>" >> "$HTML_FILE"
    
    log_output "Report saved to:"
    log_output "  HTML file: $HTML_FILE"
    
    exit 1
else
    log_output "Neo4j connection successful!"
fi

# Terminal colors for visual hierarchy
BOLD="\033[1m"
CYAN="\033[36m"     # Section headers
GREEN="\033[32m"    # Good indicators
YELLOW="\033[33m"   # Warning indicators
RED="\033[31m"      # Critical indicators
BLUE="\033[34m"     # Properties
MAGENTA="\033[35m"  # Relationships
WHITE="\033[37m"    # Primary text
GRAY="\033[90m"     # Secondary text
RESET="\033[0m"

# Display characters
NODE_CHAR="◉"
PROPERTY_CHAR="•"
REL_CHAR="→"
SUGGEST_CHAR="✓"
INDENT="  "

# Clear the screen for a clean report
clear

# Print header
log_output "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════════╗${RESET}"
log_output "${BOLD}${CYAN}║              NEO4J DATABASE STRUCTURE REPORT                       ║${RESET}"
log_output "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════════╝${RESET}"
log_output "Generated: $(date +"%Y-%m-%d %H:%M")"
log_output ""

# Get database size info and overall structure
log_output "${BOLD}${CYAN}DATABASE OVERVIEW${RESET}"
log_output "${BOLD}${WHITE}Basic metrics:${RESET}"

# Fix the UNION query by ensuring column names are the same
cypher-shell -u $NEO4J_USER -p $NEO4J_PASSWORD --format plain <<< "
MATCH (n) RETURN 'Nodes' as metric, count(n) as count
UNION ALL
MATCH ()-[r]->() RETURN 'Relationships' as metric, count(r) as count
UNION ALL
MATCH (n) RETURN 'Node types' as metric, count(distinct labels(n)) as count
UNION ALL
MATCH ()-[r]->() RETURN 'Relationship types' as metric, count(distinct type(r)) as count
" | grep -v "^$" | tail -n +3 | while read -r line; do
  # Remove quotes and commas from output
  clean_line=$(echo "$line" | tr -d '",')
  # Split by whitespace and take first part as metric, rest as count
  metric=$(echo "$clean_line" | awk '{print $1}')
  count=$(echo "$clean_line" | awk '{$1=""; print $0}' | xargs)
  log_output "${INDENT}${PROPERTY_CHAR} ${metric}: ${count}"
done
log_output ""

# Get node types and counts
log_output "${BOLD}${CYAN}NODE TYPES${RESET}"

cypher-shell -u $NEO4J_USER -p $NEO4J_PASSWORD --format plain <<< "
MATCH (n)
WITH labels(n)[0] AS nodeType, count(*) AS count
RETURN nodeType, count
ORDER BY count DESC;
" | while read -r line; do
  if [[ ! -z $line && $line != "nodeType count" ]]; then
    # Clean up output by removing quotes and commas
    clean_line=$(echo "$line" | tr -d '",')
    node_type=$(echo "$clean_line" | awk '{print $1}')
    count_str=$(echo "$clean_line" | awk '{print $2}')
    
    # Format with fixed widths for alignment
    formatted_node_type=$(printf "%-25s" "$node_type")
    
    # Validate that count is a number
    if [[ "$count_str" =~ ^[0-9]+$ ]]; then
      formatted_count=$(printf "%7d" "$count_str")
    else
      formatted_count="       ?"
    fi
    
    log_output "${WHITE}${NODE_CHAR} ${BOLD}${formatted_node_type}${RESET} ${GRAY}(${formatted_count} nodes)${RESET}"
  fi
done
log_output ""

# Get relationship summary 
log_output "${BOLD}${CYAN}RELATIONSHIP TYPES${RESET}"

cypher-shell -u $NEO4J_USER -p $NEO4J_PASSWORD --format plain <<< "
MATCH ()-[r]->()
WITH type(r) AS relType, count(*) AS count
RETURN relType, count
ORDER BY count DESC;
" | while read -r line; do
  if [[ ! -z $line && $line != "relType count" ]]; then
    # Clean up output by removing quotes and commas
    clean_line=$(echo "$line" | tr -d '",')
    rel_type=$(echo "$clean_line" | awk '{print $1}')
    count_str=$(echo "$clean_line" | awk '{print $2}')
    
    # Format with fixed widths for alignment
    formatted_rel_type=$(printf "%-25s" "$rel_type")
    
    # Validate that count is a number
    if [[ "$count_str" =~ ^[0-9]+$ ]]; then
      formatted_count=$(printf "%7d" "$count_str")
    else
      formatted_count="       ?"
    fi
    
    log_output "${MAGENTA}${NODE_CHAR} ${BOLD}${formatted_rel_type}${RESET} ${GRAY}(${formatted_count} relationships)${RESET}"
  fi
done
log_output ""

# Get comprehensive graph structure
log_output "${BOLD}${CYAN}GRAPH STRUCTURE${RESET}"
log_output "${WHITE}Node relationships (showing the primary connections):${RESET}"

# Get connections between node types
results=$(cypher-shell -u $NEO4J_USER -p $NEO4J_PASSWORD --format plain << EOF
// Graph structure showing how node types interconnect
MATCH (a)-[r]->(b)
WITH 
  labels(a)[0] AS sourceLabel, 
  type(r) AS relType, 
  labels(b)[0] AS targetLabel,
  count(*) AS relationshipCount,
  collect(distinct id(a)) AS sourceNodes,
  collect(distinct id(b)) AS targetNodes
WITH 
  sourceLabel,
  targetLabel, 
  relType,
  relationshipCount,
  size(sourceNodes) AS uniqueSourceCount,
  size(targetNodes) AS uniqueTargetCount
RETURN 
  sourceLabel, relType, targetLabel, relationshipCount, uniqueSourceCount, uniqueTargetCount
ORDER BY sourceLabel, relationshipCount DESC
EOF
)

# Process and display results in a hierarchical structure
current_source=""
echo "$results" | tail -n +3 | while IFS= read -r line; do
  # Clean up all fields by removing quotes, commas, and parentheses
  clean_line=$(echo "$line" | tr -d '",()[]')
  
  source_label=$(echo "$clean_line" | awk '{print $1}')
  rel_type=$(echo "$clean_line" | awk '{print $2}')
  target_label=$(echo "$clean_line" | awk '{print $3}')
  rel_count=$(echo "$clean_line" | awk '{print $4}')
  source_count=$(echo "$clean_line" | awk '{print $5}')
  target_count=$(echo "$clean_line" | awk '{print $6}')
  
  if [[ "$source_label" != "$current_source" ]]; then
    log_output "${CYAN}${NODE_CHAR} ${BOLD}$source_label${RESET} ${GRAY}(${source_count} nodes)${RESET}"
    current_source="$source_label"
  fi
  
  # Format all fields with fixed width
  formatted_rel_type=$(printf "%-20s" "$rel_type")
  formatted_rel_count=$(printf "%7d" "$rel_count")
  formatted_target_label=$(printf "%-15s" "$target_label")
  formatted_target_count=$(printf "%7d" "$target_count")
  
  # Display relationship with indentation and aligned numbers
  log_output "${INDENT}${GREEN}├──[${RESET}${MAGENTA}${formatted_rel_type}${RESET}${GREEN} (${formatted_rel_count})]${REL_CHAR}${RESET} ${BLUE}${formatted_target_label}${RESET} ${GRAY}(${formatted_target_count})${RESET}"
done
log_output ""

# Get property summaries for each node type
log_output "${BOLD}${CYAN}NODE PROPERTIES${RESET}"
log_output "${WHITE}Showing properties for each node type with present/missing counts:${RESET}"

# Fix: Removed redundant secondary header that was causing duplication
cypher-shell -u $NEO4J_USER -p $NEO4J_PASSWORD --format plain <<< "
MATCH (n)
WITH labels(n)[0] AS nodeType, count(*) AS nodeCount
MATCH (m)
WHERE labels(m)[0] = nodeType
UNWIND keys(m) AS propName
WITH nodeType, nodeCount, propName, count(m) AS propCount
RETURN nodeType, nodeCount, propName, propCount, 
       toInteger(100.0 * propCount / nodeCount) AS percentage
ORDER BY nodeType, percentage DESC;
" | while read -r line; do
  if [[ ! -z $line && $line != "nodeType nodeCount propName propCount percentage" ]]; then
    # Clean up output by removing quotes, parentheses, and commas
    clean_line=$(echo "$line" | tr -d '",')
    node_type=$(echo "$clean_line" | awk '{print $1}')
    node_count=$(echo "$clean_line" | awk '{print $2}')
    prop_name=$(echo "$clean_line" | awk '{print $3}')
    prop_count=$(echo "$clean_line" | awk '{print $4}')
    percentage=$(echo "$clean_line" | awk '{print $5}')
    
    # Format with fixed widths for alignment - handle invalid numbers by checking
    formatted_node_type=$(printf "%-25s" "$node_type")
    formatted_prop_name=$(printf "%-30s" "$prop_name")
    
    # Check if prop_count is a valid number
    if [[ "$prop_count" =~ ^[0-9]+$ ]]; then
      formatted_prop_count=$(printf "%7d" "$prop_count")
    else
      formatted_prop_count="       ?"
    fi
    
    # Check if percentage is a valid number
    if [[ "$percentage" =~ ^[0-9]+$ ]]; then
      formatted_percentage=$(printf "%3d" "$percentage")
    else
      formatted_percentage="  ?"
    fi
    
    if [[ "$current_node_type" != "$node_type" ]]; then
      current_node_type=$node_type
      log_output ""
      log_output "${WHITE}${NODE_CHAR} ${BOLD}${formatted_node_type}${RESET}"
    fi
    
    # Print different colors based on percentage - use numeric check
    if [[ "$percentage" =~ ^[0-9]+$ ]]; then
      if (( percentage == 100 )); then
        log_output "      ${GREEN}${formatted_prop_name}${RESET}  ${GRAY}(present in ${formatted_prop_count} nodes, ${formatted_percentage}%)${RESET}"
      elif (( percentage >= 90 )); then
        log_output "      ${YELLOW}${formatted_prop_name}${RESET}  ${GRAY}(present in ${formatted_prop_count} nodes, ${formatted_percentage}%)${RESET}"
      else
        log_output "      ${RED}${formatted_prop_name}${RESET}  ${GRAY}(present in ${formatted_prop_count} nodes, ${formatted_percentage}%)${RESET}"
      fi
    else
      # Handle case when percentage is not a valid number
      log_output "      ${RED}${formatted_prop_name}${RESET}  ${GRAY}(present in ${formatted_prop_count} nodes, unknown%)${RESET}"
    fi
  fi
done
log_output ""

# Display relationship properties
log_output "\n${BOLD}${CYAN}RELATIONSHIP PROPERTIES${RESET}"
log_output "${WHITE}Showing properties for each relationship type with present/missing counts:${RESET}"

# Fix: Removed redundant secondary header that was causing duplication
cypher-shell -u $NEO4J_USER -p $NEO4J_PASSWORD --format plain <<< "
MATCH ()-[r]->()
WITH type(r) AS relType, count(*) AS relCount
MATCH ()-[s]->()
WHERE type(s) = relType
UNWIND keys(s) AS propName
WITH relType, relCount, propName, count(s) AS propCount
RETURN relType, relCount, propName, propCount, 
       toInteger(100.0 * propCount / relCount) AS percentage
ORDER BY relType, percentage DESC;
" | while read -r line; do
  if [[ ! -z $line && $line != "relType relCount propName propCount percentage" ]]; then
    # Clean up output by removing quotes, parentheses, and commas
    clean_line=$(echo "$line" | tr -d '",')
    rel_type=$(echo "$clean_line" | awk '{print $1}')
    rel_count=$(echo "$clean_line" | awk '{print $2}')
    prop_name=$(echo "$clean_line" | awk '{print $3}')
    prop_count=$(echo "$clean_line" | awk '{print $4}')
    percentage=$(echo "$clean_line" | awk '{print $5}')
    
    # Format with fixed widths for alignment - handle invalid numbers by checking
    formatted_rel_type=$(printf "%-25s" "$rel_type")
    formatted_prop_name=$(printf "%-30s" "$prop_name")
    
    # Check if prop_count is a valid number
    if [[ "$prop_count" =~ ^[0-9]+$ ]]; then
      formatted_prop_count=$(printf "%7d" "$prop_count")
    else
      formatted_prop_count="       ?"
    fi
    
    # Check if percentage is a valid number
    if [[ "$percentage" =~ ^[0-9]+$ ]]; then
      formatted_percentage=$(printf "%3d" "$percentage")
    else
      formatted_percentage="  ?"
    fi
    
    if [[ "$current_rel_type" != "$rel_type" ]]; then
      current_rel_type=$rel_type
      log_output ""
      log_output "${MAGENTA}${NODE_CHAR} ${BOLD}${formatted_rel_type}${RESET}"
    fi
    
    # Print different colors based on percentage - use numeric check
    if [[ "$percentage" =~ ^[0-9]+$ ]]; then
      if (( percentage == 100 )); then
        log_output "      ${GREEN}${formatted_prop_name}${RESET}  ${GRAY}(present in ${formatted_prop_count} relationships, ${formatted_percentage}%)${RESET}"
      elif (( percentage >= 90 )); then
        log_output "      ${YELLOW}${formatted_prop_name}${RESET}  ${GRAY}(present in ${formatted_prop_count} relationships, ${formatted_percentage}%)${RESET}"
      else
        log_output "      ${RED}${formatted_prop_name}${RESET}  ${GRAY}(present in ${formatted_prop_count} relationships, ${formatted_percentage}%)${RESET}"
      fi
    else
      # Handle case when percentage is not a valid number
      log_output "      ${RED}${formatted_prop_name}${RESET}  ${GRAY}(present in ${formatted_prop_count} relationships, unknown%)${RESET}"
    fi
  fi
done
log_output ""

# Show a quick summary message
log_output "${BOLD}${CYAN}REPORT COMPLETE${RESET}" 

# Close HTML file
echo "</pre></body></html>" >> "$HTML_FILE"

# Print file location
log_output ""
log_output "Report saved to:"
log_output "${GRAY}Report saved to: ${HTML_FILE}${RESET}" 