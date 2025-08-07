#!/usr/bin/env python3
"""Execute Cypher templates from the template library."""

from neo4j import GraphDatabase
from templates import TEMPLATES

# Neo4j connection settings (using NodePort)
URI = "bolt://localhost:30687"
USER = "neo4j"
PASS = "Next2020#"

driver = GraphDatabase.driver(URI, auth=(USER, PASS))

# Recovery templates for zero-result queries
RECOVERY_TEMPLATES = {
    "compare_two_entities_metric": "fact_lookup",  # Fallback to single company
    "news_recent_by_company": "news_between_dates",  # Try broader date range
    "latest_report_for_company": "entity_list",  # Show available reports
    "fact_lookup": "fact_by_dimension",  # Try dimensional breakdown
    "price_history_date_range": "price_stats_over_period",  # Show aggregates
}

def execute(template_id: str, **kwargs):
    """Execute a template with the given parameters."""
    tpl = TEMPLATES[template_id]
    
    # Parameter sanity-check
    missing = [p for p in tpl["params"] if p not in kwargs]
    if missing:
        raise ValueError(f"Missing params: {missing}")
    
    # Replace label/relationship parameters with actual values
    # Neo4j doesn't support parameterized labels/types
    cypher = tpl["cypher"]
    for param, value in kwargs.items():
        # Replace $Label, $Rel, etc. patterns for structural elements
        if param in ["Label", "L1", "L2", "L3", "Rel", "Rel1", "Rel2", "RelType", 
                     "RelMetric", "Event", "Target", "Metric1", "Metric2", 
                     "CompanyLabel", "SrcLabel", "TgtLabel", "SubRel", "SubLabel",
                     "EventA", "EventB", "RelA", "RelB", "prop", "srcProp", 
                     "dateProp", "groupProp", "aggProp", "metric", "index", 
                     "dir", "cmp", "order", "agg", "aggFunc"]:
            # Safety: Only allow alphanumeric and underscore for structural elements
            import re
            safe_value = re.sub(r'[^A-Za-z0-9_]', '', str(value))
            if safe_value != str(value):
                print(f"Warning: Sanitized '{param}' value from '{value}' to '{safe_value}'")
            cypher = cypher.replace(f"${param}", safe_value)
    
    # Keep only true parameter values for the query
    params = {k: v for k, v in kwargs.items() if f"${k}" in tpl["cypher"]}
    
    with driver.session() as sess:
        results = sess.run(cypher, params).data()
        
        # Recovery logic: Try fallback template if no results
        if not results and template_id in RECOVERY_TEMPLATES:
            fallback_id = RECOVERY_TEMPLATES[template_id]
            fallback_template = TEMPLATES[fallback_id]
            
            # Check if we have the required params for fallback
            fallback_params = {}
            can_fallback = True
            
            for param in fallback_template['params']:
                if param in kwargs:
                    fallback_params[param] = kwargs[param]
                else:
                    # Try to provide sensible defaults
                    if param == 'limit':
                        fallback_params[param] = 10
                    elif param == 'days':
                        fallback_params[param] = 30
                    elif param == 'from':
                        fallback_params[param] = '2024-01-01'
                    elif param == 'to':
                        fallback_params[param] = '2024-12-31'
                    else:
                        can_fallback = False
                        break
            
            if can_fallback:
                print(f"No results, trying fallback: {fallback_id}")
                return execute(fallback_id, **fallback_params)
        
        return results

if __name__ == "__main__":
    # Test with a simple template
    print("=== Simple Test: List 3 Companies ===")
    results = execute("entity_list", Label="Company", limit=3)
    for r in results:
        print(f"- {r['n']['name']} ({r['n']['ticker']})")
    
    print("\n=== Complex Test: Compare Revenue ===")
    try:
        results = execute(
            "compare_two_entities_metric",
            ticker1="AAPL",
            ticker2="MSFT", 
            qname="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
        )
        print(results if results else "No data found")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Recovery Logic Test ===")
    # Test with a query that might return no results
    try:
        results = execute(
            "news_recent_by_company",
            ticker="ZZZZ",  # Fake ticker
            days=1,
            limit=5
        )
        print(f"Results: {len(results)} items")
    except Exception as e:
        print(f"Error: {e}")