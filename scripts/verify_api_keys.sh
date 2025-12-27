#!/bin/bash
# Script to verify API keys configuration

echo "=== API Keys Verification ==="
echo ""

# Load environment from .env
source /home/faisal/EventMarketDB/.env

echo "1. From .env file:"
echo "   OPENAI_API_KEY: ${OPENAI_API_KEY:0:50}..."
echo "   GEMINI_API_KEY: ${GEMINI_API_KEY}"
echo ""

echo "2. From ~/.bashrc:"
grep -E "^export (OPENAI_API_KEY|GEMINI_API_KEY)" ~/.bashrc | sed 's/export /   /' | sed 's/=.*$/=.../'
echo ""

echo "3. From Python eventtrader/keys.py:"
cd /home/faisal/EventMarketDB
python3 -c "
from eventtrader import keys
print(f'   OPENAI_API_KEY: {keys.OPENAI_API_KEY[:50] if keys.OPENAI_API_KEY else None}...')
print(f'   GEMINI_API_KEY: {keys.GEMINI_API_KEY if keys.GEMINI_API_KEY else None}')
"
echo ""

echo "4. From Kubernetes secrets:"
for ns in processing mcp-services; do
    echo "   Namespace: $ns"
    kubectl get secret eventtrader-secrets -n $ns -o json 2>/dev/null | jq -r '.data | keys[]' | grep -E "OPENAI_API_KEY|GEMINI_API_KEY" | sed 's/^/     - /'
done
echo ""

echo "5. Sample pod verification (edge-writer):"
POD=$(kubectl get pods -n processing -l app=edge-writer -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ ! -z "$POD" ]; then
    kubectl exec -n processing $POD -- sh -c 'echo "   OPENAI_API_KEY: $(echo $OPENAI_API_KEY | cut -c1-50)..." && echo "   GEMINI_API_KEY: $GEMINI_API_KEY"' 2>/dev/null
else
    echo "   No edge-writer pod found"
fi

echo ""
echo "=== Verification Complete ==="