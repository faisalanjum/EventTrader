#!/usr/bin/env bash
# Deploy all components: event-trader, xbrl-worker, report-enricher
# Usage: ./scripts/deploy-all.sh

set -e
cd "$(dirname "$0")/.."    # repo root

echo "=== Deploying All Components ==="
echo ""

# Pull latest code once for all
echo "▶︎ git pull"
git pull
echo ""

# Deploy each component
components=("event-trader" "xbrl-worker" "report-enricher")
for comp in "${components[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "▶︎ Deploying $comp"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Build and push (using existing script)
    ./scripts/build_push.sh "$comp"
    
    # Rollout (using existing script)
    ./scripts/rollout.sh "$comp"
    
    echo "✔︎ $comp deployed"
    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✔︎ All components deployed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Check deployment status:"
echo "  kubectl get deployments -n processing"
echo "  kubectl get pods -n processing"