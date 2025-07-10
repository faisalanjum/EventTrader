-- XBRL Optimization Complete Test Script
-- Run this to verify all components work correctly

-- 1. Check all constraints exist
SHOW CONSTRAINTS 
WHERE name IN ['hasConcept_key', 'hasUnit_key', 'hasPeriod_key']
RETURN name, type;

-- 2. Verify relationship keys are unique and not null
MATCH (f:Fact)-[r:HAS_CONCEPT|HAS_UNIT|HAS_PERIOD]->()
WITH type(r) as rel_type, 
     count(r) as total_rels,
     count(r.key) as rels_with_key,
     count(DISTINCT r.key) as unique_keys
RETURN rel_type, total_rels, rels_with_key, unique_keys,
       CASE WHEN total_rels = rels_with_key AND total_rels = unique_keys 
            THEN '✓ PASS' 
            ELSE '✗ FAIL' END as status
ORDER BY rel_type;

-- 3. Check Context->HAS_PERIOD relationships also have keys
MATCH (c:Context)-[r:HAS_PERIOD]->(p:Period)
WITH count(r) as total_context_period,
     count(r.key) as with_key
RETURN 'Context->HAS_PERIOD' as relationship,
       total_context_period,
       with_key,
       CASE WHEN total_context_period = with_key 
            THEN '✓ PASS' 
            ELSE '✗ FAIL' END as status;

-- 4. Test constraint enforcement (should fail with duplicate key)
-- DO NOT RUN IN PRODUCTION - This is just to verify constraint works
/*
MATCH (f:Fact) WITH f LIMIT 1
MATCH (c:Concept) WITH f, c LIMIT 1
CREATE (f)-[r:HAS_CONCEPT {key: f.id}]->(c)
-- Should get: Neo.ClientError.Schema.ConstraintValidationFailed
*/

-- 5. Performance test - measure lookup time with key
MATCH (f:Fact) WITH f LIMIT 100
WITH collect(f.id) as fact_ids
WITH fact_ids, datetime() as start_time
UNWIND fact_ids as fid
MATCH (:Fact)-[r:HAS_CONCEPT {key: fid}]->(:Concept)
WITH start_time, count(r) as found
RETURN found as relationships_found,
       duration.between(start_time, datetime()).milliseconds as lookup_time_ms;