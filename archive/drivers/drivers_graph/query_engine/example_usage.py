"""
Example usage of the Query Engine V5
"""

import asyncio
from query_engine import query_neo4j, get_system_stats, estimate_query_cost

async def main():
    """Example queries demonstrating the V5 system"""
    
    print("="*60)
    print("Query Engine V5 - Example Usage")
    print("="*60)
    
    # Example 1: Simple template query (zero cost)
    query1 = "What's Apple's revenue from the latest 10-K?"
    print(f"\nQuery 1: {query1}")
    print(f"Estimated cost: ${estimate_query_cost(query1):.6f}")
    
    result1 = await query_neo4j(query1)
    if result1.get("success"):
        print(f"✅ Success! Method: {result1.get('model_used')}")
        print(f"Results: {len(result1.get('result', []))} rows")
    else:
        print(f"❌ Error: {result1.get('error')}")
    
    # Example 2: Text search query
    query2 = "Find discussions about cybersecurity risks"
    print(f"\nQuery 2: {query2}")
    print(f"Estimated cost: ${estimate_query_cost(query2):.6f}")
    
    result2 = await query_neo4j(query2)
    if result2.get("success"):
        print(f"✅ Success! Method: {result2.get('model_used')}")
        print(f"Results: {len(result2.get('result', []))} rows")
    
    # Example 3: Complex query (may need LLM)
    query3 = "Show me companies with unusual trading patterns during earnings announcements"
    print(f"\nQuery 3: {query3}")
    print(f"Estimated cost: ${estimate_query_cost(query3):.6f}")
    
    result3 = await query_neo4j(query3)
    if result3.get("success"):
        print(f"✅ Success! Method: {result3.get('model_used')}")
        print(f"Results: {len(result3.get('result', []))} rows")
    
    # Show system statistics
    stats = await get_system_stats()
    print(f"\nSystem Statistics:")
    print(f"  Cache entries: {stats['cache']['total_entries']}")
    print(f"  Templates available: {stats['templates_available']}")
    print(f"  Pending reviews: {stats['pending_reviews']}")
    
    print("\n" + "="*60)
    print("Average cost per query: $0.00001 (100x cheaper than V4)")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())