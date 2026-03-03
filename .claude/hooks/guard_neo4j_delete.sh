#!/bin/bash
# guard_neo4j_delete.sh
# Blocks destructive Neo4j Cypher operations (DELETE, DROP, REMOVE)
# via write_neo4j_cypher unless explicitly approved by the user.

INPUT=$(cat 2>/dev/null) || INPUT=""
if [ -z "$INPUT" ]; then
  echo "{}"
  exit 0
fi

QUERY=$(echo "$INPUT" | jq -r '.tool_input.query // empty')
if [ -z "$QUERY" ]; then
  echo "{}"
  exit 0
fi

# Normalize to uppercase for pattern matching
UPPER_QUERY=$(echo "$QUERY" | tr '[:lower:]' '[:upper:]')

# Check for destructive operations
# DETACH DELETE — removes nodes and all their relationships
# DELETE — removes nodes/relationships
# DROP — drops constraints/indexes
# REMOVE — removes properties/labels
# CALL apoc.*.delete / CALL apoc.*.drop — APOC destructive procs

BLOCKED=""

if echo "$UPPER_QUERY" | grep -qE '\bDETACH\s+DELETE\b'; then
  BLOCKED="DETACH DELETE"
elif echo "$UPPER_QUERY" | grep -qE '\bDELETE\b'; then
  BLOCKED="DELETE"
elif echo "$UPPER_QUERY" | grep -qE '\bDROP\b'; then
  BLOCKED="DROP"
elif echo "$UPPER_QUERY" | grep -qE '\bREMOVE\b'; then
  BLOCKED="REMOVE"
elif echo "$UPPER_QUERY" | grep -qiE 'CALL\s+apoc\.\S*\.(delete|drop|remove)'; then
  BLOCKED="APOC destructive procedure"
fi

if [ -n "$BLOCKED" ]; then
  # Truncate query for the message (first 200 chars)
  SHORT_QUERY="${QUERY:0:200}"
  echo "{\"decision\":\"block\",\"reason\":\"BLOCKED: Destructive Neo4j operation ($BLOCKED) requires user approval. Query: ${SHORT_QUERY}\"}"
  exit 0
fi

echo "{}"
exit 0
