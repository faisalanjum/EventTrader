#!/usr/bin/env python3
"""Simple CLI for the Neo4j Query Engine using LLM Router."""

import os
import sys
from pathlib import Path

# Check for API key
if not os.getenv("OPENAI_API_KEY"):
    print("❌ Error: OPENAI_API_KEY environment variable not set")
    print("   Set it with: export OPENAI_API_KEY='your-key-here'")
    sys.exit(1)

try:
    from llm_router import LLMRouter
except ImportError as e:
    print("❌ Error: Missing dependencies")
    print("   Install with: pip install langchain-openai neo4j")
    sys.exit(1)

def main():
    """Interactive query CLI."""
    print("🚀 Neo4j Query Engine (LLM Router)")
    print("=" * 50)
    print("Type your questions in natural language.")
    print("Type 'exit' to quit, 'help' for examples.")
    print("=" * 50)
    
    # Initialize router
    try:
        router = LLMRouter()
        print("✅ Connected to Neo4j and OpenAI\n")
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        sys.exit(1)
    
    # Example queries
    examples = [
        "Show me 5 companies",
        "What's Apple's latest 10-K?",
        "Compare Apple and Microsoft revenue",
        "Show XBRL processing status",
        "News for AAPL in last 30 days",
        "explain how to get Apple stock prices",
        "Who owns unicorns?"  # Unknown query
    ]
    
    while True:
        try:
            # Get user input
            query = input("\n💬 Query: ").strip()
            
            if query.lower() == 'exit':
                print("👋 Goodbye!")
                break
            
            if query.lower() == 'help':
                print("\n📚 Example queries:")
                for ex in examples:
                    print(f"   - {ex}")
                continue
            
            if not query:
                continue
            
            # Route query
            print("🔄 Processing...")
            result = router.route(query)
            
            # Display results
            if result["status"] == "success":
                print(f"\n✅ Template: {result['intent']}")
                
                if "plan_type" in result:
                    print(f"📊 {result['plan_type']} Output:")
                    print("-" * 40)
                    output = result.get('plan') or result.get('profile', '')
                    print(output[:500] + "..." if len(output) > 500 else output)
                else:
                    print(f"📊 Results: {result['count']} rows")
                    
                    if result['count'] > 0 and result['data']:
                        print("\n🔍 Sample data:")
                        # Show first 3 results
                        for i, row in enumerate(result['data'][:3]):
                            print(f"\n[{i+1}]", end="")
                            # Pretty print each field
                            for key, value in list(row.items())[:3]:  # First 3 fields
                                if isinstance(value, dict):
                                    print(f"\n  {key}: <dict with {len(value)} keys>")
                                else:
                                    print(f"\n  {key}: {value}")
                        
                        if result['count'] > 3:
                            print(f"\n... and {result['count'] - 3} more results")
            
            elif result["status"] == "unknown":
                print(f"\n❓ Unknown query type")
                print(f"📝 Reason: {result['reason']}")
                print(f"💡 {result['suggestion']}")
                if result.get('logged'):
                    print("📋 Query logged for future template development")
            
            else:  # error
                print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
                if result.get('params'):
                    print(f"📝 Attempted params: {result['params']}")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            print("   Try again or type 'exit' to quit")

if __name__ == "__main__":
    main()