#!/bin/bash
# Quick test script to verify the Query Engine v2 is working

echo "🚀 Neo4j Query Engine v2 - Quick Test"
echo "===================================="

# Check if OpenAI key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set. LLM routing will not work."
    echo "   Set with: export OPENAI_API_KEY='your-key'"
else
    echo "✅ OpenAI API key found"
fi

echo ""
echo "1️⃣ Testing template validation (EXPLAIN)..."
echo "-------------------------------------------"
python validate_templates.py | grep -E "(✅|❌|SUMMARY)" | tail -10

echo ""
echo "2️⃣ Testing basic template execution..."
echo "---------------------------------------"
python -c "
from run_template import execute
result = execute('entity_list', Label='Company', limit=2)
print(f'✅ Found {len(result)} companies')
"

echo ""
echo "3️⃣ Testing unknown query logging..."
echo "------------------------------------"
if [ -f "unknown_queries.log" ]; then
    echo "📋 Recent unknown queries:"
    tail -3 unknown_queries.log
else
    echo "📋 No unknown queries logged yet"
fi

echo ""
echo "✅ Quick test complete!"
echo ""
echo "📚 Next steps:"
echo "   - Run full validation: python validate_templates.py"
echo "   - Run with profiling: python validate_templates.py PROFILE"
echo "   - Run smoke tests: python smoke_test.py"
echo "   - Interactive CLI: python query_cli.py"
echo ""