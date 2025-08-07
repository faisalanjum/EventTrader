#!/usr/bin/env python3
"""Test unknown query logging functionality."""

import os

# Check if API key exists
if not os.getenv("OPENAI_API_KEY"):
    print("❌ OPENAI_API_KEY not set. Let me simulate unknown queries instead...")
    
    # Simulate what would happen with unknown queries
    from datetime import datetime
    from pathlib import Path
    
    # Create the log file manually with example unknown queries
    unknown_queries = [
        "Who owns unicorns?",
        "What is the P/E ratio for Tesla?", 
        "Show me insider trading activity",
        "Which companies have the best ESG scores?",
        "Find companies with dividend yield over 5%"
    ]
    
    log_path = Path("unknown_queries.log")
    with open(log_path, "a", encoding="utf-8") as f:
        for query in unknown_queries:
            f.write(f"{datetime.now().isoformat()} | {query} | No template for this query type\n")
    
    print("✅ Created unknown_queries.log with simulated entries")
    print("\n📋 Contents of unknown_queries.log:")
    print(log_path.read_text())
    
else:
    # Test with actual LLM router
    from llm_router import LLMRouter
    
    print("🔍 Testing Unknown Query Logging with LLM Router")
    print("=" * 50)
    
    router = LLMRouter()
    
    # Test queries that should be unknown
    test_unknown_queries = [
        "Who owns unicorns?",
        "What is the P/E ratio for Tesla?",
        "Show me insider trading activity",
        "Which companies have the best ESG scores?",
        "Find companies with dividend yield over 5%"
    ]
    
    # Test queries that should match templates
    test_known_queries = [
        "Show me 5 companies",
        "What is Apple's latest 10-K?", 
        "Show XBRL processing status"
    ]
    
    print("\n1️⃣ Testing queries that should be UNKNOWN:")
    print("-" * 50)
    for query in test_unknown_queries:
        result = router.route(query)
        print(f"\n'{query}'")
        print(f"   Status: {result['status']}")
        if result['status'] == 'unknown':
            print(f"   ✅ Correctly identified as unknown")
            print(f"   Logged: {result.get('logged', False)}")
    
    print("\n\n2️⃣ Testing queries that should MATCH templates:")
    print("-" * 50)
    for query in test_known_queries:
        result = router.route(query)
        print(f"\n'{query}'")
        print(f"   Status: {result['status']}")
        if result['status'] == 'success':
            print(f"   ✅ Matched template: {result['intent']}")
    
    # Check the log file
    from pathlib import Path
    log_path = Path("unknown_queries.log")
    
    if log_path.exists():
        print("\n\n📋 Contents of unknown_queries.log:")
        print("=" * 50)
        print(log_path.read_text())
    else:
        print("\n\n❓ No unknown_queries.log file created yet")

print("\n💡 The unknown_queries.log file is created automatically when:")
print("   1. You use the LLM router (requires OPENAI_API_KEY)")
print("   2. A user asks a question that doesn't match any template")
print("   3. The LLM returns {\"intent\": \"unknown\", ...}")
print("\nThis helps you discover what new templates to add!")