-- Test Script for XBRL Performance Optimization
-- Run this after deployment to verify constraints are working

-- 1. Check constraints exist
SHOW CONSTRAINTS 
WHERE name IN ['hasConcept_key', 'hasUnit_key', 'hasPeriod_key'];

-- 2. Test creating a relationship with key (should succeed)
MATCH (f:Fact) WITH f LIMIT 1
MATCH (c:Concept) WITH f, c LIMIT 1
MERGE (f)-[r:HAS_CONCEPT {key: f.id}]->(c)
SET r.test = true
RETURN f.id, c.id, r.key;

-- 3. Try creating duplicate with same key (should not create new relationship)
MATCH (f:Fact)-[r:HAS_CONCEPT {test: true}]->(c:Concept)
WITH f, c, r
MERGE (f)-[r2:HAS_CONCEPT {key: f.id}]->(c)
WITH f, c, count(r) as before_count
MATCH (f)-[r3:HAS_CONCEPT]->(c)
RETURN f.id, c.id, before_count, count(r3) as after_count;
-- Expected: before_count = after_count = 1

-- 4. Cleanup test relationship
MATCH ()-[r:HAS_CONCEPT {test: true}]->()
DELETE r;

-- 5. Performance test - measure merge time
MATCH (f:Fact) WITH f LIMIT 100
MATCH (c:Concept) WITH f, c LIMIT 1
WITH collect({f: f, c: c}) as pairs
WITH datetime() as start_time, pairs
UNWIND pairs as pair
MERGE (pair.f)-[r:HAS_CONCEPT {key: pair.f.id}]->(pair.c)
WITH start_time, count(r) as created
RETURN created, duration.between(start_time, datetime()).milliseconds as milliseconds;