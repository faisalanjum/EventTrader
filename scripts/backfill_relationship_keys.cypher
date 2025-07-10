-- XBRL Relationship Key Backfill Script
-- Run this AFTER deploying the constraint updates but BEFORE deploying merge_relationships updates
-- This prevents duplicate relationships during migration

-- Step 1: Check how many relationships need backfilling
MATCH (f:Fact)-[r:HAS_CONCEPT|HAS_UNIT|HAS_PERIOD]->() 
WHERE r.key IS NULL
RETURN type(r) as relationship_type, count(r) as count
ORDER BY relationship_type;

-- Step 2: Backfill all relationships in batches
-- Run this query repeatedly until it returns done=0
CALL {
  MATCH (f:Fact)-[r:HAS_CONCEPT|HAS_UNIT|HAS_PERIOD]->() 
  WHERE r.key IS NULL
  WITH r, f LIMIT 50000
  SET r.key = f.id
  RETURN count(*) AS done
} IN TRANSACTIONS OF 50000 ROWS;

-- Step 3: Verify backfill is complete
MATCH (f:Fact)-[r:HAS_CONCEPT|HAS_UNIT|HAS_PERIOD]->() 
WHERE r.key IS NULL
RETURN count(r) as remaining_without_key;

-- Step 4: Verify no duplicates exist
MATCH (f:Fact)-[r:HAS_CONCEPT]->(c:Concept)
WITH f, c, count(r) as rel_count
WHERE rel_count > 1
RETURN count(*) as duplicate_concept_relationships;

MATCH (f:Fact)-[r:HAS_UNIT]->(u:Unit)
WITH f, u, count(r) as rel_count
WHERE rel_count > 1
RETURN count(*) as duplicate_unit_relationships;

MATCH (f:Fact)-[r:HAS_PERIOD]->(p:Period)
WITH f, p, count(r) as rel_count
WHERE rel_count > 1
RETURN count(*) as duplicate_period_relationships;