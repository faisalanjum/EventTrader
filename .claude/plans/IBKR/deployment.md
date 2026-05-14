# IBKR MCP — Operational Reference

> **Functional reference** (tool capabilities, scanner codes, recipes, known bugs):
> see [`capabilities.md`](capabilities.md). This file is the K8s/runbook side.

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

- **Live**: READ_ONLY_API=no. Account summary, positions, historical bars, scanner all work. **Prices return null** — no paid market data subscription on the account. To enable streaming `get_price`/`get_tickers`, subscribe to 3 L1 feeds at **USD $4.50/mo total** (NASDAQ Network C/UTP + NYSE Network A/CTA + Network B). All standalone, no $10 bundle prerequisite. Skip OPRA unless predictor adds IV consumption (it doesn't as of 2026-05-12 — grep `.claude/skills/earnings-*` for `implied|straddle|opra` before adding). Skip all bundles, indices, L2, futures feeds. Full rationale + rejection list: `~/.claude/projects/-home-faisal-EventMarketDB/memory/project_ibkr_market_data.md`. Historical bars work free regardless.
- **Paper**: Full access. Prices, positions, account ($1.1M CAD paper balance), historical, scanner all work. Trading enabled.
- **Market data types**: Live = type 1 (real-time) / type 2 (frozen post-market). Paper = type 3 (delayed). This is hardcoded in `app/services/history.py` and `app/services/market_data.py`.
- **Custom code** in `EventMarketDB/ibkr-mcp-server/` (local fork of omdv, committed as a subdirectory of EventMarketDB git):
  - `get_account_summary` — balances, margins, PnL
  - `get_positions` null crash fix
  - Order management: market, limit, stop, bracket, trailing stop, bracket+trailing, advanced (any IB type via conId or symbol), modify, cancel, open orders
  - OrderClient uses dedicated IB() connection (clientId=1) separate from market data
  - Advanced endpoint: `extra="forbid"` rejects typos, conId for options/futures, auto-maps any ib_async Order field
  - ~40 more Order fields commented in AdvancedOrderRequest for easy activation

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

Live currently has `READ_ONLY_API=no` (account data works, order endpoints exist but untested on live).
```bash
# To lock down to read-only:
kubectl set env deployment/ibkr-ib-gateway -n mcp-services READ_ONLY_API=yes
```

## Rebuild MCP Server After Code Changes

```bash
# IMPORTANT: build from the EventMarketDB-tracked subdirectory, NOT a standalone clone.
# The standalone clone at ~/ibkr-mcp-server was historically a decoy with only upstream
# code (no smart-fix-1 modifications). It was removed 2026-05-12 to prevent confusion.
cd /home/faisal/EventMarketDB/ibkr-mcp-server
docker build -t ibkr-mcp-server:<new-tag> .
docker save ibkr-mcp-server:<new-tag> | sudo ctr -n k8s.io images import -
kubectl set image deployment/ibkr -n mcp-services ibkr-mcp-server=ibkr-mcp-server:<new-tag>
kubectl set image deployment/ibkr-paper -n mcp-services ibkr-mcp-server=ibkr-mcp-server:<new-tag>
# Then exit + restart Claude Code session to refresh MCP handles.
```

## Add New MCP Tools

1. `app/services/xxx.py` — service class inheriting `IBClient`
2. `app/api/ibkr/xxx.py` — FastAPI route
3. `app/services/interfaces.py` — add to `IBInterface` MRO
4. `app/api/ibkr/__init__.py` — add `from .xxx import *`
5. Rebuild + deploy (see above)

## Rollback Image Pin (per-contract tradingHours, 2026-05-14)

| Image | Tag | Docker SHA256 (image ID) | Containerd OCI digest |
|---|---|---|---|
| **Two-back** | `smart-fix-1` | `1a12619e0cafc39755c435da8de21f1a213b4496f55e214ffadda6dfce022390` | `d72b7f9691ceb5e34fe6ed6c3a5f1eb95ffb23947e2b60f449bfbcd32a81d7e2` |
| **Previous (rollback target)** | `ext-hours-v3` | `13b4eae9b862d1ef94eaa7e9296604dfdbeacbae787bf01d45fd17947bb70393` | `f6b60314c7bb4b3f4335bd7319d34a10059eb7d25623baddd2125b5e968f64fa` |
| **Current (per-contract hours)** | `ext-hours-v4` | `84dee3a5604823c3a05e078b1e601d885acaff5c677ccbda49a9af778cd444e3` | `7ab9e097d11d8291486a381dead00787b70942875766e0afca89e2814688ae90` |

> **Note**: `ext-hours-v1` was abandoned — it was built from the wrong source tree (a standalone clone that didn't have the smart-fix-1 modifications committed). `ext-hours-v3` was the first image built from `EventMarketDB/ibkr-mcp-server/` (true source of truth). `ext-hours-v4` adds per-contract `tradingHours` lookup on top of v3.

**Rollback commands** (~30 seconds for both deployments):

```bash
# Live MCP rollback to v3 (one step back, recommended)
kubectl set image deployment/ibkr -n mcp-services \
  ibkr-mcp-server=ibkr-mcp-server:ext-hours-v3

# Paper MCP rollback to v3
kubectl set image deployment/ibkr-paper -n mcp-services \
  ibkr-mcp-server=ibkr-mcp-server:ext-hours-v3

# Verify
kubectl -n mcp-services rollout status deployment/ibkr
kubectl -n mcp-services rollout status deployment/ibkr-paper

# After rollback: exit + restart Claude Code session to refresh MCP handles.
```

**What changed in ext-hours-v4** (in case rollback needed for forensics):
- **NEW** `app/services/trading_hours.py` — pure parser + 6h conId cache + `is_contract_open(ib, contract)` (asset-class-agnostic)
- `app/services/history.py::get_current_price()` — swapped `self._is_market_open()` → `await is_contract_open(self.ib, contract)`
- `app/services/market_data.py::get_tickers()` — swapped `self._is_market_open()` → `any(await asyncio.gather(*[is_contract_open(self.ib, c) for c in qualified_contracts]))`
- `app/services/client.py::_is_market_open()` — **UNCHANGED, KEPT AS LEGACY FALLBACK**
- All Phase 1 (is_realtime, market_data_type, -1 sentinel handling) **UNCHANGED**
- All smart-fix-1 (/livez, /readyz, heartbeat, reconnect-backoff) **UNCHANGED**
- Tests: `tests/test_trading_hours.py` (33 cases) — 61/61 total pass
- Live validation 2026-05-14 06:55 ET: AAPL/JPM/XLK premarket return is_realtime=true type=1; SPX/VIX correctly fall back is_realtime=false type=2

**What changed in ext-hours-v3** (in case full rollback to smart-fix-1 needed for forensics):
- `app/services/client.py::_is_market_open()` — widened window from RTH-only (09:30-16:00 ET) to 04:00-20:00 ET on NYSE session days
- `app/services/history.py::_to_float()` — now also nulls IB's -1 sentinel (was only nulling NaN)
- `app/services/history.py::get_current_price()` — falls through to historical-bar path when real-time ticker has all-null `last`/`close`
- `app/services/market_data.py` — 2 spots: added `and v != -1` to ticker field cleaning
- **`app/models/history.py::PriceSnapshot`** — 2 NEW REQUIRED FIELDS:
  - `is_realtime: bool` — True iff IB served live market-data mode (type 1) with data; bots check this before trusting bid/ask/last as current
  - `market_data_type: int` — IB's raw classification (1=Live, 2=Frozen, 3=Delayed, 4=Delayed-Frozen)
- `app/services/history.py` — both `PriceSnapshot` constructors now set the two new fields (live path: `is_realtime=(ticker.marketDataType == 1)`, historical fallback: `is_realtime=False, market_data_type=2`)
- `uv.lock` — exchange-calendars 4.10.1 → 4.13.2; added pytest as dev dep
- Tests: `tests/test_market_open.py` (14 cases) + `tests/test_to_float.py` (7 cases) + `tests/test_realtime_flag.py` (7 cases) — 28 total, all pass

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
