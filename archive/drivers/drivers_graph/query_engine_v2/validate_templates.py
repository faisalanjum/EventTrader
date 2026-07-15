#!/usr/bin/env python3
"""Validate all templates with EXPLAIN or PROFILE to ensure they parse and use indexes."""

from templates import TEMPLATES
from run_template import driver
import sys

# Default test parameters for validation
DEFAULT_PARAMS = {
    "ticker": "AAPL",
    "ticker1": "AAPL", 
    "ticker2": "MSFT",
    "form": "10-K",
    "qname": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
    "from": "2024-01-01",
    "to": "2024-12-31",
    "limit": 10,
    "days": 30,
    "Label": "Company",
    "L1": "Company",
    "L2": "Report", 
    "L3": "News",
    "prop": "name",
    "value": "Apple",
    "text": "revenue",
    "index": "company_ft",
    "order": "DESC",
    "industry": "Technology",
    "sector": "Technology",
    "Rel": "HAS_PRICE",
    "Rel1": "PRIMARY_FILER",
    "Rel2": "HAS_XBRL",
    "RelType": "INFLUENCES",
    "RelMetric": "HAS_METRIC",
    "Event": "News",
    "Target": "Company",
    "Metric1": "Revenue",
    "Metric2": "NetIncome",
    "CompanyLabel": "Company",
    "SrcLabel": "Company",
    "TgtLabel": "Report",
    "SubRel": "HAS_SECTION",
    "SubLabel": "Section",
    "EventA": "News",
    "EventB": "Report",
    "RelA": "INFLUENCES",
    "RelB": "PRIMARY_FILER",
    "srcProp": "ticker",
    "srcValue": "AAPL",
    "dateProp": "created",
    "groupProp": "sector",
    "aggProp": "mkt_cap",
    "aggFunc": "avg",
    "metric": "close",
    "dir": "->",
    "cmp": ">",
    "agg": "sum",
    "date": "2024-01-15",
    "delta": 0.05,
    "id1": "123",
    "id2": "456",
    "k": 10,
    "embedding": "[0.1, 0.2, 0.3]",
    "keyword": "revenue",
    "parent_qname": "us-gaap:NetIncomeLoss",
    "section_keyword": "income",
    "term": "revenue",
    "search_term": "climate",
    "section_filter": "RiskFactors",
    "section_name": "RiskFactors",
    "event_section_name": "Item2.02",
    "exhibit_number": "EX-99.1",
    "statement_type": "BalanceSheets",
    "form_type_filter": "10-K",
    "impact_threshold": 0.05,
    "none": ""  # For xbrl_process_status
}

def validate_template(name, template, mode="EXPLAIN"):
    """Validate a single template with EXPLAIN or PROFILE."""
    print(f"\n{'='*60}")
    print(f"Validating ({mode}): {name}")
    print(f"Comment: {template['comment']}")
    print(f"Params: {template['params']}")
    print("-" * 60)
    
    try:
        # Build parameters for this template
        params = {}
        for param in template['params']:
            if param in DEFAULT_PARAMS:
                params[param] = DEFAULT_PARAMS[param]
            else:
                print(f"⚠️  Warning: No default value for param '{param}'")
                params[param] = "DEFAULT"
        
        # Prepare the EXPLAIN query
        cypher = template['cypher']
        
        # Replace structural elements (same logic as in execute())
        for param, value in params.items():
            if param in ["Label", "L1", "L2", "L3", "Rel", "Rel1", "Rel2", "RelType", 
                         "RelMetric", "Event", "Target", "Metric1", "Metric2", 
                         "CompanyLabel", "SrcLabel", "TgtLabel", "SubRel", "SubLabel",
                         "EventA", "EventB", "RelA", "RelB", "prop", "srcProp", 
                         "dateProp", "groupProp", "aggProp", "metric", "index", 
                         "dir", "cmp", "order", "agg", "aggFunc"]:
                cypher = cypher.replace(f"${param}", str(value))
        
        # Add EXPLAIN or PROFILE prefix
        prefixed_cypher = f"{mode} {cypher}"
        
        # Get clean params for Neo4j
        clean_params = {k: v for k, v in params.items() if f"${k}" in template["cypher"]}
        
        # Execute EXPLAIN/PROFILE
        with driver.session() as sess:
            result = sess.run(prefixed_cypher, clean_params)
            
            if mode == "PROFILE":
                # For PROFILE, we need to consume results first
                data = result.data()
                profile = result.consume().profile
                
                if profile:
                    print(f"✅ Query executed successfully! Returned {len(data)} rows")
                    profile_str = str(profile)
                    
                    # Extract db hits and rows
                    import re
                    db_hits = re.findall(r'db hits: (\d+)', profile_str)
                    total_db_hits = sum(int(h) for h in db_hits) if db_hits else 0
                    
                    print(f"📊 Total DB Hits: {total_db_hits}")
                    
                    # Check for expensive operations
                    if "AllNodesScan" in profile_str:
                        print("⚠️  WARNING: Full database scan detected!")
                    elif total_db_hits > 10000:
                        print("⚠️  WARNING: High DB hits - may need optimization")
                    
                    # Show profile preview
                    profile_lines = profile_str.split('\n')[:10]
                    print("\nProfile preview:")
                    for line in profile_lines:
                        print(f"  {line}")
                else:
                    print("❌ No profile data returned")
                    
            else:  # EXPLAIN
                plan = result.consume().plan
                
                if plan:
                    print("✅ Query parsed successfully!")
                    
                    # Check for index usage
                    plan_str = str(plan)
                    if "NodeIndexSeek" in plan_str or "NodeUniqueIndexSeek" in plan_str:
                        print("✅ Uses indexes")
                    elif "NodeByLabelScan" in plan_str:
                        print("⚠️  Uses label scan (no index)")
                    elif "AllNodesScan" in plan_str:
                        print("⚠️  WARNING: Full database scan!")
                    else:
                        print("ℹ️  Query plan type: Check manually")
                    
                    # Show first few lines of plan
                    plan_lines = plan_str.split('\n')[:5]
                    print("\nPlan preview:")
                    for line in plan_lines:
                        print(f"  {line}")
                        
                else:
                    print("❌ No query plan returned")
                
        return True
        
    except Exception as e:
        print(f"❌ VALIDATION FAILED: {type(e).__name__}")
        print(f"   Error: {str(e)}")
        if hasattr(e, 'code'):
            print(f"   Code: {e.code}")
        return False

def main():
    """Validate all templates."""
    # Check if PROFILE mode requested
    mode = "PROFILE" if len(sys.argv) > 1 and sys.argv[1].upper() == "PROFILE" else "EXPLAIN"
    
    print(f"🔍 Template Validation Report ({mode} mode)")
    print("=" * 60)
    print(f"Total templates: {len(TEMPLATES)}")
    
    # Test connection first
    try:
        with driver.session() as sess:
            sess.run("RETURN 1").single()
        print("✅ Neo4j connection successful\n")
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        sys.exit(1)
    
    # Validate each template
    passed = 0
    failed = 0
    warnings = []
    
    for name, template in TEMPLATES.items():
        if validate_template(name, template, mode):
            passed += 1
        else:
            failed += 1
            
    # Summary
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {len(TEMPLATES)}")
    print(f"🎯 Success Rate: {passed/len(TEMPLATES)*100:.1f}%")
    
    if failed > 0:
        print(f"\n⚠️  {failed} templates need attention!")
        print("   Review the errors above and fix the queries.")
    else:
        print("\n🎉 All templates validated successfully!")
    
    # Usage hint
    if mode == "EXPLAIN":
        print("\n💡 Tip: Run with 'python validate_templates.py PROFILE' to see actual execution metrics")

if __name__ == "__main__":
    main()