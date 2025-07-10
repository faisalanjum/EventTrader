#!/bin/bash
# Script to add Kubernetes files to git

echo "Adding Kubernetes recovery files to git..."

# Core K8s deployment files
git add k8s/event-trader-deployment.yaml
git add k8s/report-enricher-deployment.yaml
git add k8s/report-enricher-scaledobject.yaml
git add k8s/xbrl-worker-deployments.yaml
git add k8s/xbrl-worker-scaledobjects.yaml
git add k8s/historical-safety-config.yaml
git add k8s/neo4j-statefulset.yaml
git add k8s/.gitignore

# MCP services if you use them
git add k8s/mcp-services/*.yaml 2>/dev/null || true

# Scripts
git add scripts/deploy.sh
git add scripts/deploy-all.sh
git add scripts/setup-logging.sh

# Documentation
git add CLAUDE.md
git add kubeSetup.md

# Remove old/duplicate files from git
git rm kubeSetup_*.md 2>/dev/null || true
git rm k8s/neo4j-statefulset.yaml.backup 2>/dev/null || true

echo ""
echo "Files staged. Review with: git status"
echo ""
echo "Suggested commit message:"
echo "git commit -m 'feat: add k8s configs with KEDA autoscaling and historical safety limits'"