#!/bin/bash
# refresh-claude-token.sh — Refresh Claude OAuth token and update K8s Secret
#
# Install as cron (weekly, Sunday midnight):
#   0 0 * * 0 faisal /home/faisal/EventMarketDB/scripts/refresh-claude-token.sh
#
# Or via /etc/cron.d/claude-token-refresh:
#   0 0 * * 0 faisal /home/faisal/EventMarketDB/scripts/refresh-claude-token.sh >> /home/faisal/EventMarketDB/logs/token-refresh.log 2>&1

set -euo pipefail

NAMESPACE="processing"
SECRET_NAME="claude-auth"
DEPLOYMENT_NAME="claude-code-worker"
LOG_PREFIX="[token-refresh]"

log() {
    echo "${LOG_PREFIX} $(date '+%Y-%m-%d %H:%M:%S') $*"
}

die() {
    log "ERROR: $*" >&2
    exit 1
}

log "Starting token refresh"

# Step 1: Refresh the OAuth token via Claude CLI
log "Running: claude setup-token"
if ! /home/faisal/.local/bin/claude setup-token 2>&1; then
    die "claude setup-token failed"
fi

# Step 2: Read the refreshed token from credentials
CREDS_FILE="$HOME/.claude/.credentials.json"
[ -f "$CREDS_FILE" ] || die "Credentials file not found: $CREDS_FILE"

TOKEN=$(python3 -c "
import json, sys
with open('$CREDS_FILE') as f:
    d = json.load(f)
# The token is stored under claudeAiOauth
oauth = d.get('claudeAiOauth', {})
token = oauth.get('accessToken') or oauth.get('token', '')
if not token:
    print('ERROR: No token found in credentials', file=sys.stderr)
    sys.exit(1)
print(token)
")
[ -n "$TOKEN" ] || die "Failed to extract token from credentials"
log "Token extracted (${#TOKEN} chars)"

# Step 3: Update the K8s Secret (create-or-replace pattern)
log "Updating Secret/${SECRET_NAME} in namespace ${NAMESPACE}"
if ! kubectl create secret generic "$SECRET_NAME" \
    --from-literal=CLAUDE_CODE_OAUTH_TOKEN="$TOKEN" \
    --dry-run=client -o yaml | kubectl apply -f - -n "$NAMESPACE" 2>&1; then
    die "Failed to update K8s secret"
fi
log "Secret updated"

# Step 4: Restart the worker pod to pick up the new token
log "Restarting ${DEPLOYMENT_NAME}"
if ! kubectl rollout restart deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE" 2>&1; then
    log "WARNING: rollout restart failed (worker may not be running — KEDA scale-to-zero)"
fi

log "Token refresh complete"
