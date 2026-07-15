// Keyword Search Queries for EventMarketDB
// Fixed versions addressing type checking and data type handling issues

// ============================================================================
// VERSION 1: ROBUST TYPE-SAFE VERSION (RECOMMENDED)
// ============================================================================
// This version uses proper CASE statements to handle different data types
// and avoids issues with complex types like lists or maps

MATCH (c:Company)-[*0..3]-(n)
WHERE c.name =~ '(?i).*ultrathink.*'
WITH n, c
// Filter nodes that have at least one property matching our keywords
WITH n, c, keys(n) as nodeKeys
UNWIND nodeKeys as prop
WITH n, c, prop
WHERE prop <> 'embedding' AND prop <> 'vector' AND NOT prop STARTS WITH 'embed'
  AND n[prop] IS NOT NULL
WITH n, c, prop, n[prop] as value
// Safely check if the value contains our keywords
WITH n, c, prop, value
WHERE CASE
  WHEN value IS :: STRING THEN value =~ '(?i).*(guidance|outlook|forecast|expectation|projection).*'
  WHEN value IS :: INTEGER OR value IS :: FLOAT OR value IS :: BOOLEAN THEN 
    toString(value) =~ '(?i).*(guidance|outlook|forecast|expectation|projection).*'
  ELSE false
END
WITH DISTINCT n, c
RETURN DISTINCT 
  labels(n)[0] as NodeType,
  COALESCE(n.accessionNo, n.id, toString(id(n))) as AccessionNo,
  n.form_type as FormType,
  n.filing_date as FilingDate,
  [prop IN keys(n) WHERE 
    prop <> 'embedding' AND prop <> 'vector' AND NOT prop STARTS WITH 'embed'
    AND n[prop] IS NOT NULL
    AND CASE
      WHEN n[prop] IS :: STRING THEN n[prop] =~ '(?i).*(guidance|outlook|forecast|expectation|projection).*'
      WHEN n[prop] IS :: INTEGER OR n[prop] IS :: FLOAT OR n[prop] IS :: BOOLEAN THEN 
        toString(n[prop]) =~ '(?i).*(guidance|outlook|forecast|expectation|projection).*'
      ELSE false
    END | 
    prop + ': ' + substring(
      CASE 
        WHEN n[prop] IS :: STRING THEN n[prop]
        ELSE toString(n[prop])
      END, 0, 200)
  ] as MatchingProperties
ORDER BY n.filing_date DESC
LIMIT 100;

// ============================================================================
// VERSION 2: SIMPLIFIED VERSION (LESS TYPE CHECKING)
// ============================================================================
// This version excludes lists but doesn't do extensive type checking
// Use this if Version 1 has performance issues

MATCH (c:Company)-[*0..3]-(n)
WHERE c.name =~ '(?i).*ultrathink.*'
WITH n, c
WHERE ANY(prop IN keys(n) WHERE 
  prop <> 'embedding' AND prop <> 'vector' AND NOT prop STARTS WITH 'embed'
  AND n[prop] IS NOT NULL
  AND NOT (n[prop] IS :: LIST)
  AND toString(n[prop]) =~ '(?i).*(guidance|outlook|forecast|expectation|projection).*'
)
RETURN DISTINCT 
  labels(n)[0] as NodeType,
  n.accessionNo as AccessionNo,
  n.form_type as FormType,
  n.filing_date as FilingDate,
  [prop IN keys(n) WHERE 
    prop <> 'embedding' AND prop <> 'vector' AND NOT prop STARTS WITH 'embed'
    AND n[prop] IS NOT NULL
    AND NOT (n[prop] IS :: LIST)
    AND toString(n[prop]) =~ '(?i).*(guidance|outlook|forecast|expectation|projection).*' | 
    prop + ': ' + substring(toString(n[prop]), 0, 200)] as MatchingProperties
ORDER BY n.filing_date DESC
LIMIT 100;

// ============================================================================
// VERSION 3: SPECIFIC PROPERTY VERSION
// ============================================================================
// If you know which specific properties to search, this is most efficient

MATCH (c:Company)-[*0..3]-(n)
WHERE c.name =~ '(?i).*ultrathink.*'
  AND (
    (EXISTS(n.text) AND n.text =~ '(?i).*(guidance|outlook|forecast|expectation|projection).*')
    OR (EXISTS(n.content) AND n.content =~ '(?i).*(guidance|outlook|forecast|expectation|projection).*')
    OR (EXISTS(n.description) AND n.description =~ '(?i).*(guidance|outlook|forecast|expectation|projection).*')
    OR (EXISTS(n.summary) AND n.summary =~ '(?i).*(guidance|outlook|forecast|expectation|projection).*')
    OR (EXISTS(n.title) AND n.title =~ '(?i).*(guidance|outlook|forecast|expectation|projection).*')
    OR (EXISTS(n.body) AND n.body =~ '(?i).*(guidance|outlook|forecast|expectation|projection).*')
    OR (EXISTS(n.headline) AND n.headline =~ '(?i).*(guidance|outlook|forecast|expectation|projection).*')
  )
RETURN DISTINCT 
  labels(n)[0] as NodeType,
  COALESCE(n.accessionNo, n.id, toString(id(n))) as AccessionNo,
  n.form_type as FormType,
  n.filing_date as FilingDate,
  [prop IN ['text', 'content', 'description', 'summary', 'title', 'body', 'headline'] WHERE 
    EXISTS(n[prop]) AND n[prop] =~ '(?i).*(guidance|outlook|forecast|expectation|projection).*' | 
    prop + ': ' + substring(n[prop], 0, 200)
  ] as MatchingProperties
ORDER BY n.filing_date DESC
LIMIT 100;

// ============================================================================
// USAGE EXAMPLES
// ============================================================================

// Example 1: Search for specific company by CIK instead of name
// Replace: WHERE c.name =~ '(?i).*ultrathink.*'
// With:    WHERE c.cik = '0001804220'

// Example 2: Search for different keywords
// Replace: '(?i).*(guidance|outlook|forecast|expectation|projection).*'
// With:    '(?i).*(revenue|earnings|profit|loss|margin).*'

// Example 3: Limit search depth (faster)
// Replace: MATCH (c:Company)-[*0..3]-(n)
// With:    MATCH (c:Company)-[*0..2]-(n)

// Example 4: Search only specific node types
// Add after the MATCH: WHERE labels(n) IN [['Report'], ['News'], ['Section']]

// ============================================================================
// PERFORMANCE TIPS
// ============================================================================
// 1. Use CIK instead of name pattern matching when possible
// 2. Reduce relationship depth for faster queries
// 3. Add node label filters to reduce search space
// 4. Consider creating full-text indexes for frequently searched properties
// 5. Use Version 3 (specific properties) when you know the schema

// ============================================================================
// TROUBLESHOOTING
// ============================================================================
// If query times out:
// - Reduce relationship depth (*0..2 instead of *0..3)
// - Search for more specific company names or use CIK
// - Limit to specific node types
// - Reduce LIMIT value

// If no results found:
// - Check company name spelling
// - Try broader keyword patterns
// - Verify the company exists: MATCH (c:Company) WHERE c.name CONTAINS 'ultra' RETURN c
// - Check if nodes have the expected properties