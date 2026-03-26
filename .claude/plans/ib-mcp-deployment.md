# IBKR MCP — Operational Reference

## What's Running

4 pods in `mcp-services` namespace on `minisforum`:

| Pod | Image | Connects To | Purpose |
|---|---|---|---|
| ibkr-ib-gateway | gnzsnz/ib-gateway:stable | IB servers (live U5113348) | Live IB Gateway, auto-login via IBC |
| ibkr (Helm) | omdv/ibkr-mcp-server:latest | ibkr-ib-gateway:4003 | Live MCP — prices, account, scanner, history |
| ibkr-paper-gateway | gnzsnz/ib-gateway:stable | IB servers (paper DU4502670) | Paper IB Gateway, auto-login via IBC |
| ibkr-paper | omdv/ibkr-mcp-server:latest | ibkr-paper-gateway:4004 | Paper MCP — trading, walk-forward testing |

## Ports

| Port | Service | Type |
|---|---|---|
| **31100** | ibkr (live MCP) | NodePort |
| **31101** | ibkr-paper (paper MCP) | NodePort |
| 4003 | ibkr-ib-gateway (live TWS relay) | ClusterIP |
| 4004 | ibkr-paper-gateway (paper TWS relay) | ClusterIP |

## MCP Config (`.mcp.json`)

Both entries use `type: "sse"` (NOT `"http"` — server uses legacy SSE transport).
Auth tokens stored in K8s secrets: `ibkr-mcp-auth`, `ibkr-paper-mcp-auth`.
Permissions pre-allowed in `.claude/settings.json`: `mcp__ibkr-live`, `mcp__ibkr-paper`.

## Current State

- **Live**: READ_ONLY_API=no. Account summary, positions, historical bars, scanner all work. **Prices return null** — IB API market data subscription not enabled (TWS-only subscription). Enable in IB Account Management for real-time.
- **Paper**: Full access. Prices, positions, account ($1.1M CAD paper balance), historical, scanner all work. Trading enabled.
- **Market data types**: Live = type 1 (real-time) / type 2 (frozen post-market). Paper = type 3 (delayed). This is hardcoded in `app/services/history.py` and `app/services/market_data.py`.
- **Custom code**: We added `get_account_summary` endpoint and fixed `get_positions` null crash in the local omdv clone at `/home/faisal/ibkr-mcp-server/`.

## K8s Files

| File | Manages |
|---|---|
| `k8s/mcp-services/ibkr-values.yaml` | Helm values for live gateway + live MCP |
| `k8s/mcp-services/ibkr-paper-gateway.yaml` | Paper gateway deployment + service |
| `k8s/mcp-services/ibkr-paper-mcp.yaml` | Paper MCP deployment + service |

Helm release: `ibkr` in mcp-services. Paper resources are standalone kubectl manifests.

## Secrets

| Secret | Contains |
|---|---|
| ibkr-credentials | IB username + password (shared by both gateways) |
| ibkr-mcp-auth | Live MCP bearer token |
| ibkr-paper-mcp-auth | Paper MCP bearer token |

## Re-Login (After Pod Restart or Weekly 2FA Expiry)

Gateways auto-login via IBC on pod restart. You only need to act if 2FA is required:

1. **Watch your phone** — approve the IB notification when it arrives
2. Verify: `kubectl logs -n mcp-services -l app.kubernetes.io/component=ib-gateway --tail=5` → look for "Login has completed"
3. For paper: `kubectl logs -n mcp-services -l app.kubernetes.io/component=paper-gateway --tail=5`
4. If stuck, delete the pod and let K8s recreate: `kubectl delete pod -n mcp-services -l app.kubernetes.io/component=ib-gateway`

Both gateways auto-restart daily at 06:00 AM via `AUTO_RESTART_TIME`.

## Enable Live Trading

```bash
# Already set to no — this is the current state
# To revert to read-only: change "no" to "yes"
kubectl set env deployment/ibkr-ib-gateway -n mcp-services READ_ONLY_API=no
```

## Rebuild MCP Server After Code Changes

```bash
cd /home/faisal/ibkr-mcp-server
docker build -t ghcr.io/omdv/ibkr-mcp-server:latest .
docker save ghcr.io/omdv/ibkr-mcp-server:latest | sudo ctr -n k8s.io images import -
kubectl rollout restart deployment ibkr ibkr-paper -n mcp-services
```

## Add New MCP Tools

1. `app/services/xxx.py` — service class inheriting `IBClient`
2. `app/api/ibkr/xxx.py` — FastAPI route
3. `app/services/interfaces.py` — add to `IBInterface` MRO
4. `app/api/ibkr/__init__.py` — add `from .xxx import *`
5. Rebuild + deploy (see above)

## Connection Reset & Recovery

| Event | Frequency | Action |
|---|---|---|
| Daily auto-restart | 06:00 AM daily | Automatic — approve 2FA on phone if prompted |
| 2FA token expiry | ~7 days | Approve 2FA on phone (up to 2 notifications — one per gateway) |
| Pod crash | Rare | K8s auto-recreates, approve 2FA if prompted |

**Recovery if broken:**
```bash
kubectl get pods -n mcp-services -l app.kubernetes.io/instance=ibkr
# If CrashLoopBackOff or 0/1:
kubectl delete pod -n mcp-services -l app.kubernetes.io/component=ib-gateway
kubectl delete pod -n mcp-services -l app.kubernetes.io/component=paper-gateway
# Approve 2FA on phone, then verify:
kubectl logs -n mcp-services -l app.kubernetes.io/component=ib-gateway --tail=3
# Should say: "Login has completed"
```

## DO NOT USE

- **rcontesti/IB_MCP** (Client Portal Gateway) — ssodh/init broken in containers
- **extrange/ibkr image** — API socket stuck in PRELOGON state
- **TRADING_MODE=both** in single gateway — paper session fails to authenticate
- **`type: "http"` in .mcp.json** — use `type: "sse"` (server uses legacy SSE transport)
