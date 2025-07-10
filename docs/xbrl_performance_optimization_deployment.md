# XBRL Performance Optimization Deployment Guide

## Overview
This optimization adds relationship key constraints to eliminate lock contention on shared nodes (Concepts, Units, Periods) during XBRL processing. Expected performance improvement: 400-500x for HAS_CONCEPT/HAS_UNIT/HAS_PERIOD merges.

## Changes Made

### 1. Neo4jManager.py - Added Relationship Key Constraints
Added three new constraints in `create_indexes()` method (lines 249-277):
- `hasConcept_key`: Unique key constraint for HAS_CONCEPT relationships
- `hasUnit_key`: Unique key constraint for HAS_UNIT relationships  
- `hasPeriod_key`: Unique key constraint for HAS_PERIOD relationships

### 2. Neo4jManager.py - Updated merge_relationships()
Modified the relationship creation logic (lines 648-656) to use the key property for fact lookup relationships:
```python
MERGE (s)-[r:{rel_type.value} {{key: param.source_id}}]->(t)
```

## Deployment Steps

### Step 1: Deploy Constraint Updates
Deploy the updated Neo4jManager.py with the new constraints. The constraints will be created automatically on the next node export operation.

### Step 2: Run Backfill Script (CRITICAL - Do this BEFORE processing any reports)
Execute the backfill script to add key properties to existing relationships:

```bash
# Connect to Neo4j
kubectl exec -it neo4j-0 -n neo4j -- cypher-shell -u neo4j -p $NEO4J_PASSWORD

# Run the backfill query (repeat until done=0)
CALL {
  MATCH (f:Fact)-[r:HAS_CONCEPT|HAS_UNIT|HAS_PERIOD]->() 
  WHERE r.key IS NULL
  WITH r, f LIMIT 50000
  SET r.key = f.id
  RETURN count(*) AS done
} IN TRANSACTIONS OF 50000 ROWS;

# Verify backfill is complete
MATCH (f:Fact)-[r:HAS_CONCEPT|HAS_UNIT|HAS_PERIOD]->() 
WHERE r.key IS NULL
RETURN count(r) as remaining_without_key;
```

### Step 3: Deploy merge_relationships Update
Only after backfill is complete, deploy the merge_relationships update that uses the key property.

### Step 4: Test with Single 10-K
Process a single 10-K document and monitor the logs:
```bash
# Monitor XBRL worker logs
kubectl logs -f <xbrl-heavy-pod> -n processing | grep "HAS_CONCEPT\|HAS_UNIT\|HAS_PERIOD"
```

Expected: Merge operations should complete in seconds instead of minutes.

### Step 5: Verify No Duplicates
```sql
-- Check for duplicate relationships
MATCH (f:Fact)-[r:HAS_CONCEPT]->(c:Concept)
WITH f, c, count(r) as rel_count
WHERE rel_count > 1
RETURN count(*) as duplicate_concept_relationships;
```

## Rollback Plan
If issues occur:
1. Revert Neo4jManager.py to previous version
2. The constraints can remain (they don't affect old code)
3. Existing key properties on relationships are harmless

## Performance Expectations
- Before: HAS_CONCEPT merge takes 7+ minutes for 836 relationships
- After: Should complete in <1 second
- Overall 10-K processing: From 60+ minutes to <10 minutes