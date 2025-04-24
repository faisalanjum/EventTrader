#!/bin/bash
# partial_reset.sh - Script to preserve Redis namespaces and Neo4j initialization data
# Uses APOC for Neo4j operations for better performance with large datasets

# Get the workspace directory
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WORKSPACE_DIR"

# Define the namespaces to preserve
NAMESPACES=(
  "admin:tradable_universe:stock_universe*"
  "admin:tradable_universe:symbols*"
)

# Create temp directory for backup files
TEMP_DIR=$(mktemp -d)
BACKUP_SCRIPT="$TEMP_DIR/redis_backup.sh"
echo "#!/bin/bash" > $BACKUP_SCRIPT

# Process each namespace
for NAMESPACE in "${NAMESPACES[@]}"; do
  # Get all keys in this namespace
  KEYS=$(redis-cli --raw keys "$NAMESPACE")
  
  # Process each key by type
  for KEY in $KEYS; do
    TYPE=$(redis-cli type "$KEY")
    case $TYPE in
      string)
        VALUE=$(redis-cli get "$KEY")
        echo "redis-cli set \"$KEY\" \"$VALUE\"" >> $BACKUP_SCRIPT
        ;;
      hash)
        echo -n "redis-cli hmset \"$KEY\" " >> $BACKUP_SCRIPT
        redis-cli hgetall "$KEY" | while read -r FIELD; do
          read -r VALUE
          echo -n "\"$FIELD\" \"$VALUE\" " >> $BACKUP_SCRIPT
        done
        echo "" >> $BACKUP_SCRIPT
        ;;
      list)
        VALUES=$(redis-cli lrange "$KEY" 0 -1)
        if [ ! -z "$VALUES" ]; then
          echo -n "redis-cli rpush \"$KEY\" " >> $BACKUP_SCRIPT
          for VALUE in $VALUES; do
            echo -n "\"$VALUE\" " >> $BACKUP_SCRIPT
          done
          echo "" >> $BACKUP_SCRIPT
        fi
        ;;
      set)
        VALUES=$(redis-cli smembers "$KEY")
        if [ ! -z "$VALUES" ]; then
          echo -n "redis-cli sadd \"$KEY\" " >> $BACKUP_SCRIPT
          for VALUE in $VALUES; do
            echo -n "\"$VALUE\" " >> $BACKUP_SCRIPT
          done
          echo "" >> $BACKUP_SCRIPT
        fi
        ;;
      zset)
        redis-cli zrange "$KEY" 0 -1 withscores | while read -r MEMBER; do
          read -r SCORE
          echo "redis-cli zadd \"$KEY\" $SCORE \"$MEMBER\"" >> $BACKUP_SCRIPT
        done
        ;;
    esac
  done
done

# Make the backup script executable
chmod +x $BACKUP_SCRIPT

# ==================== CLEAR & RESTORE REDIS ====================
echo "Clearing Redis and restoring preserved namespaces..."

# Flush all Redis data
redis-cli flushall

# Restore preserved keys from backup script
$BACKUP_SCRIPT

# ==================== CLEAR NEO4J WHILE PRESERVING INIT DATA (WITH APOC) ====================
echo "Clearing Neo4j data while preserving initialization using APOC..."

# Neo4j credentials - extract from .env file or use defaults
if [ -f "$WORKSPACE_DIR/.env" ]; then
  echo "Loading Neo4j credentials from .env file..."
  # Try to get credentials from .env file
  NEO4J_USER_ENV=$(grep -E '^NEO4J_USERNAME|^NEO4J_USER' "$WORKSPACE_DIR/.env" | sed -E 's/^NEO4J_USERNAME=?|^NEO4J_USER=?//' | tr -d '"' | tr -d "'")
  NEO4J_PASSWORD_ENV=$(grep -E '^NEO4J_PASSWORD' "$WORKSPACE_DIR/.env" | sed -E 's/^NEO4J_PASSWORD=?//' | tr -d '"' | tr -d "'")
  
  if [ -n "$NEO4J_USER_ENV" ] && [ -n "$NEO4J_PASSWORD_ENV" ]; then
    NEO4J_USER="$NEO4J_USER_ENV"
    NEO4J_PASSWORD="$NEO4J_PASSWORD_ENV"
    echo "Using Neo4j credentials from .env file: user=$NEO4J_USER, password=***"
  else
    # Hardcoded fallback
    echo "Using hardcoded fallback credentials"
    NEO4J_USER="neo4j"
    NEO4J_PASSWORD="Next2020#"
  fi
else
  # Fallback to environment variables or defaults
  NEO4J_USER="${NEO4J_USER:-neo4j}"
  NEO4J_PASSWORD="${NEO4J_PASSWORD:-Next2020#}"
  echo "Using Neo4j credentials from environment: user=$NEO4J_USER, password=***"
fi

# Test Neo4j connection before proceeding
echo "Testing Neo4j connection..."
CONNECTION_TEST=$(cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" --format plain "RETURN 1 as test" 2>&1)
if [[ "$CONNECTION_TEST" == *"Failure to establish connection"* ]] || [[ "$CONNECTION_TEST" == *"unauthorized"* ]]; then
    echo "ERROR: Could not connect to Neo4j database. Please check credentials and Neo4j status."
    echo "Connection error: $CONNECTION_TEST"
    echo ""
    echo "You can manually specify credentials with:"
    echo "NEO4J_USER=neo4j NEO4J_PASSWORD='Next2020#' $0"
    exit 1
else
    echo "Neo4j connection successful!"
fi

# Cypher query to preserve initialization nodes while clearing everything else with APOC
echo "Checking if APOC is installed..."
cypher-shell -u $NEO4J_USER -p $NEO4J_PASSWORD "RETURN apoc.version() AS APOC_Version"

echo "Deleting non-preserved relationships..."
cypher-shell -u $NEO4J_USER -p $NEO4J_PASSWORD "
MATCH ()-[r]->() 
WHERE NOT type(r) IN ['NEXT', 'BELONGS_TO', 'RELATED_TO', 'HAS_PRICE', 'HAS_SUB_REPORT', 
                       'HAS_DIVIDEND', 'DECLARED_DIVIDEND', 'HAS_SPLIT', 'DECLARED_SPLIT']
DELETE r
"

echo "Deleting non-preserved nodes..."
cypher-shell -u $NEO4J_USER -p $NEO4J_PASSWORD "
MATCH (n)
WHERE NOT any(label IN labels(n) WHERE label IN ['Date', 'Company', 'Industry', 'Sector', 'MarketIndex', 
                                                 'AdminReport', 'Dividend', 'Split'])
DETACH DELETE n
"

echo "Verifying results..."
cypher-shell -u $NEO4J_USER -p $NEO4J_PASSWORD "
MATCH (n) 
WITH labels(n) AS nodeLabels, count(*) AS nodeCount
RETURN nodeLabels, nodeCount
ORDER BY nodeCount DESC
"

cypher-shell -u $NEO4J_USER -p $NEO4J_PASSWORD "
MATCH ()-[r]->()
WITH type(r) AS relType, count(*) AS relCount
RETURN relType, relCount
ORDER BY relCount DESC
"

# Clean up temp files
rm -rf $TEMP_DIR

echo "Reset complete. Redis and Neo4j cleaned while preserving initialization data."