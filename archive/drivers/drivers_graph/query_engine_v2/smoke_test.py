#!/usr/bin/env python3
"""Comprehensive smoke test for all query templates."""

from run_template import execute
from templates import TEMPLATES
import sys
from datetime import datetime, timedelta

# Test cases for each template with realistic parameters
TEST_CASES = {
    "compare_two_entities_metric": {
        "params": {"ticker1": "AAPL", "ticker2": "MSFT", "qname": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"},
        "expect": "Compare Apple and Microsoft revenue"
    },
    "distinct_companies_with_fact": {
        "params": {"qname": "us-gaap:Assets", "from": "2023-01-01", "to": "2023-12-31", "limit": 5},
        "expect": "Companies reporting assets in 2023"
    },
    "entities_without_property": {
        "params": {"Label": "Company", "prop": "employees", "limit": 3},
        "expect": "Companies missing employee count"
    },
    "entity_filter_property": {
        "params": {"Label": "Company", "prop": "sector", "value": "Technology", "limit": 5},
        "expect": "Technology sector companies"
    },
    "entity_list": {
        "params": {"Label": "Company", "limit": 3},
        "expect": "List first 3 companies"
    },
    "entity_property_range_filter": {
        "params": {"Label": "Company", "prop": "mkt_cap", "min": 1000000000, "max": 10000000000, "limit": 5},
        "expect": "Companies with market cap 1B-10B"
    },
    "entity_search_text": {
        "params": {"Label": "Company", "prop": "name", "text": "Inc", "limit": 5},
        "expect": "Companies with 'Inc' in name"
    },
    "fact_lookup": {
        "params": {"ticker": "AAPL", "form": "10-K", "qname": "us-gaap:NetIncomeLoss"},
        "expect": "Apple's net income from 10-K"
    },
    "fact_on_report_date": {
        "params": {"ticker": "AAPL", "qname": "us-gaap:Assets", "limit": 5},
        "expect": "Facts on same date as news"
    },
    "fact_summary_aggregate": {
        "params": {"ticker": "AAPL", "qname": "us-gaap:NetIncomeLoss", "from": "2023-01-01", "to": "2023-12-31", "agg": "avg"},
        "expect": "Average net income for Apple in 2023"
    },
    "fulltext_search_section": {
        "params": {"index": "concept_ft", "text": "revenue", "limit": 3},
        "expect": "Full-text search for 'revenue'"
    },
    "hierarchy_traverse": {
        "params": {"ticker": "AAPL"},
        "expect": "Apple's organizational hierarchy"
    },
    "industry_members": {
        "params": {"industry": "SoftwareInfrastructure", "limit": 5},
        "expect": "Software infrastructure companies"
    },
    "influence_by_date": {
        "params": {"Event": "News", "Target": "Company", "ticker": "AAPL", "date": "2024-01-02", "cmp": ">", "delta": 0, "limit": 5},
        "expect": "News influencing Apple on specific date"
    },
    "latest_report_for_company": {
        "params": {"ticker": "AAPL", "form": "10-K"},
        "expect": "Apple's latest 10-K"
    },
    "metric_relation_pattern": {
        "params": {"Metric1": "Revenue", "RelMetric": "RELATES_TO", "Metric2": "NetIncome", "limit": 5},
        "expect": "Metric relationships"
    },
    "moving_average_metric": {
        "params": {"Rel": "HAS_PRICE", "Target": "Company", "ticker": "AAPL", "metric": "close", "from": "2024-01-01", "to": "2024-01-31"},
        "expect": "Moving average of Apple stock"
    },
    "news_between_dates": {
        "params": {"ticker": "AAPL", "from": "2024-01-01", "to": "2024-01-31", "limit": 5},
        "expect": "Apple news in January 2024"
    },
    "price_history_date_range": {
        "params": {"ticker": "AAPL", "from": "2024-01-01", "to": "2024-01-05"},
        "expect": "Apple price history"
    },
    "price_stats_over_period": {
        "params": {"ticker": "AAPL", "from": "2024-01-01", "to": "2024-01-31"},
        "expect": "Apple price statistics"
    },
    "rank_entities_by_property": {
        "params": {"Label": "Company", "prop": "mkt_cap", "order": "DESC", "limit": 5},
        "expect": "Top 5 companies by market cap"
    },
    "relationship_count_between_labels": {
        "params": {"L1": "Company", "Rel": "PRIMARY_FILER", "L2": "Report"},
        "expect": "Count of company-report relationships"
    },
    "relationship_exists_between_node_ids": {
        "params": {"L1": "Company", "id1": "0000320193", "Rel": "PRIMARY_FILER", "L2": "Report", "id2": "any"},
        "expect": "Check if relationship exists"
    },
    "report_count_formtype_period": {
        "params": {"form": "10-K", "from": "2023-01-01", "to": "2023-12-31"},
        "expect": "Count of 10-K reports in 2023"
    },
    "rolling_sum_metric": {
        "params": {"Rel": "HAS_PRICE", "Target": "Company", "ticker": "AAPL", "metric": "volume", "from": "2024-01-01", "to": "2024-01-31"},
        "expect": "Rolling sum of Apple volume"
    },
    "time_series_extreme_value": {
        "params": {"Rel": "HAS_PRICE", "Target": "Company", "ticker": "AAPL", "metric": "high", "from": "2024-01-01", "to": "2024-01-31", "order": "DESC"},
        "expect": "Highest Apple price in January"
    },
    "top_influence_returns": {
        "params": {"Event": "News", "Target": "Company", "metric": "daily_stock", "order": "DESC", "limit": 5},
        "expect": "Top positive stock impacts"
    },
    "transcripts_for_company": {
        "params": {"ticker": "AAPL", "limit": 3},
        "expect": "Apple earnings transcripts"
    },
    "two_hop_bridge": {
        "params": {"L1": "Company", "Rel1": "PRIMARY_FILER", "L2": "Report", "Rel2": "HAS_XBRL", "L3": "XBRLNode", "limit": 2},
        "expect": "Two-hop traversal example"
    },
    "vector_similarity_nodes": {
        "params": {"index": "company_embeddings", "k": 5, "embedding": [0.1, 0.2, 0.3], "limit": 5},
        "expect": "Vector similarity search"
    },
    "related_nodes_single_hop": {
        "params": {"SrcLabel": "Company", "srcProp": "ticker", "srcValue": "AAPL", "RelType": "PRIMARY_FILER", "dir": "->", "TgtLabel": "Report", "limit": 5},
        "expect": "Apple's reports"
    },
    "recent_entities_by_days": {
        "params": {"Label": "Report", "dateProp": "created", "days": 7, "limit": 5},
        "expect": "Reports from last 7 days"
    },
    "same_day_events_join": {
        "params": {"EventA": "News", "RelA": "INFLUENCES", "EventB": "Report", "RelB": "PRIMARY_FILER", "Target": "Company", "dateProp": "created", "limit": 5},
        "expect": "News and reports on same day"
    },
    "report_section_filter": {
        "params": {"CompanyLabel": "Company", "ticker": "AAPL", "form": "10-K", "section": "Risk", "limit": 3},
        "expect": "Risk sections in Apple 10-K"
    },
    "report_subdocument_lookup": {
        "params": {"form": "10-K", "SubRel": "HAS_SECTION", "SubLabel": "ExtractedSectionContent", "limit": 5},
        "expect": "Sections from 10-K reports"
    },
    "aggregate_property_by_group": {
        "params": {"Label": "Company", "groupProp": "sector", "aggProp": "mkt_cap", "aggFunc": "avg", "order": "DESC", "limit": 5},
        "expect": "Average market cap by sector"
    },
    "fact_by_dimension": {
        "params": {"qname": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "limit": 10},
        "expect": "Revenue broken down by dimension"
    },
    "two_dim_breakdown": {
        "params": {"qname": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "limit": 10},
        "expect": "Revenue with two dimensions"
    },
    "dimension_hierarchy": {
        "params": {"keyword": "product", "limit": 5},
        "expect": "Product dimension hierarchy"
    },
    "calculation_tree": {
        "params": {"parent_qname": "us-gaap:NetIncomeLoss"},
        "expect": "Net income calculation tree"
    },
    "presentation_outline": {
        "params": {"section_keyword": "income", "limit": 10},
        "expect": "Income statement outline"
    },
    "concept_search_text": {
        "params": {"term": "revenue", "limit": 5},
        "expect": "Search concepts for 'revenue'"
    },
    "fact_group_by_unit": {
        "params": {"limit": 5},
        "expect": "Facts grouped by unit type"
    },
    "xbrl_process_status": {
        "params": {},
        "expect": "XBRL processing status counts"
    },
    "fulltext_section_search": {
        "params": {"search_term": "climate", "section_filter": None, "limit": 5},
        "expect": "Search for 'climate' in sections"
    },
    "section_by_name": {
        "params": {"ticker": "AAPL", "section_name": "RiskFactors", "limit": 3},
        "expect": "Apple's risk factors"
    },
    "8k_section_specific": {
        "params": {"event_section_name": "Item2.02", "days": 30, "limit": 5},
        "expect": "Recent 8-K Item 2.02 events"
    },
    "exhibit_by_number": {
        "params": {"ticker": "AAPL", "exhibit_number": "EX-99.1", "limit": 3},
        "expect": "Apple's EX-99.1 exhibits"
    },
    "exhibit_fulltext_search": {
        "params": {"search_term": "agreement", "limit": 5},
        "expect": "Search exhibits for 'agreement'"
    },
    "financial_statement_content": {
        "params": {"ticker": "AAPL", "statement_type": "BalanceSheets", "limit": 3},
        "expect": "Apple's balance sheets"
    },
    "filing_text_fulltext": {
        "params": {"search_term": "revenue", "form_type_filter": "10-K", "limit": 5},
        "expect": "Search 10-K filings for 'revenue'"
    },
    "news_recent_by_company": {
        "params": {"ticker": "AAPL", "days": 30, "limit": 5},
        "expect": "Recent Apple news"
    },
    "news_fulltext_global": {
        "params": {"search_term": "technology", "limit": 5},
        "expect": "Global news search for 'technology'"
    },
    "news_high_impact": {
        "params": {"impact_threshold": 0.05, "limit": 5},
        "expect": "High impact news (>5%)"
    },
    "transcript_list_company": {
        "params": {"ticker": "AAPL", "limit": 3},
        "expect": "Apple transcript list"
    },
    "prepared_remarks_fulltext": {
        "params": {"ticker": "AAPL", "search_term": "revenue", "limit": 3},
        "expect": "Search Apple remarks for 'revenue'"
    },
    "qa_fulltext_search": {
        "params": {"ticker": "AAPL", "search_term": "guidance", "limit": 3},
        "expect": "Search Apple Q&A for 'guidance'"
    },
    "combined_content_search": {
        "params": {"search_term": "innovation", "days": 30, "limit": 5},
        "expect": "Cross-content search for 'innovation'"
    },
    "company_report_content_summary": {
        "params": {"ticker": "AAPL", "days": 90, "limit": 5},
        "expect": "Apple's content summary"
    },
    "corporate_section_search": {
        "params": {"section_name": "ExecutiveCompensation", "limit": 5},
        "expect": "Executive compensation sections"
    }
}

def run_smoke_test(name, test_case):
    """Run a single smoke test."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Purpose: {test_case['expect']}")
    print(f"Params: {test_case['params']}")
    print("-" * 60)
    
    try:
        # Execute the template
        start_time = datetime.now()
        results = execute(name, **test_case['params'])
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if results:
            print(f"✅ SUCCESS - {len(results)} results in {elapsed:.2f}s")
            # Show sample result structure
            if isinstance(results[0], dict):
                keys = list(results[0].keys())[:3]
                print(f"   Result keys: {keys}")
            return True, elapsed
        else:
            print(f"⚠️  NO RESULTS - Query executed but returned empty (might be expected)")
            return True, elapsed
            
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}")
        print(f"   Error: {str(e)}")
        return False, 0

def main():
    """Run smoke tests for all templates."""
    print("🚀 Query Engine Smoke Test")
    print("=" * 60)
    print(f"Testing {len(TEMPLATES)} templates...")
    
    # Track results
    passed = 0
    failed = 0
    no_test = 0
    total_time = 0
    
    # Run tests
    for name in TEMPLATES:
        if name in TEST_CASES:
            success, elapsed = run_smoke_test(name, TEST_CASES[name])
            if success:
                passed += 1
                total_time += elapsed
            else:
                failed += 1
        else:
            print(f"\n⚠️  No test case for: {name}")
            no_test += 1
    
    # Summary
    print(f"\n{'='*60}")
    print("SMOKE TEST SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  No test: {no_test}")
    print(f"📊 Total: {len(TEMPLATES)}")
    print(f"⏱️  Total time: {total_time:.2f}s")
    if passed > 0:
        print(f"⚡ Avg time: {total_time/passed:.2f}s per query")
    print(f"🎯 Success Rate: {passed/len(TEST_CASES)*100:.1f}%")
    
    # Exit code
    if failed > 0:
        print(f"\n❌ {failed} templates failed - review errors above")
        sys.exit(1)
    else:
        print("\n✅ All templates with test cases passed!")
        if no_test > 0:
            print(f"   (Consider adding test cases for {no_test} remaining templates)")

if __name__ == "__main__":
    main()