# IBKR Gateway Reliability — Live & Paper

**Created**: 2026-04-01
**Status**: OPEN — needs dedicated session to implement monitoring + fixes
**Impact**: Paper gateway was down 4 days (Mar 28 → Apr 1) undetected. Live gateway requires manual 2FA on every restart.

---

## Current Architecture

```
Claude Code → MCP Server (ibkr/ibkr-paper) → API Server → IB Gateway → IBKR Servers
```

| Component | Pod | Service | Port |
|-----------|-----|---------|------|
| Live MCP + API | `ibkr` | `ibkr:8000` (NodePort 31100) | 8000 |
| Live Gateway | `ibkr-ib-gateway` | `ibkr-ib-gateway:4003` | 4003 |
| Paper MCP + API | `ibkr-paper` | `ibkr-paper:8000` (NodePort 31101) | 8000 |
| Paper Gateway | `ibkr-paper-gateway` | `ibkr-paper-gateway:4004,4002` | 4004/4002 |

All in `mcp-services` namespace. Both gateways use same credentials from `ibkr-credentials` secret.

## Source-Verified Corrections (2026-04-01)

- The running live gateway does **not** currently consume the `IBC_*` ConfigMap path assumed in parts of this doc. The live deployment is using direct `gnzsnz/ib-gateway` env vars (`TWS_USERID`, `TWS_PASSWORD`, `TRADING_MODE`, `EXISTING_SESSION_DETECTED_ACTION`, etc.). Any change made only in `k8s/mcp-services/ibkr-values.yaml` or `ibkr-mcp-server/chart/templates/configmap.yaml` will not change production until the actual deployment generator is aligned and re-applied.
- Live gateway logs on 2026-04-01 show `CommandServerPort=0`, `ControlFrom=` blank, `BindAddress=` blank, and `AutoRestartTime=` blank. Paper logs show `AutoRestartTime=06:00 AM`. So any step that depends on remote IBC commands must first enable the command server in the real live deployment.
- The live service currently exposes only `4003/TCP`. There is no IBC command port exposed today.
- `ghcr.io/gnzsnz/ib-gateway` includes `Xvfb`, `x11vnc`, and `socat`, but it does **not** include `xdotool`. Dialog dismissal therefore requires either a thin derived image that installs `xdotool`, or a startup step that installs it inside the main container. The earlier assumption that a sidecar can simply reuse the same image because `xdotool` is already present is false.
- The project is locked to `ib-async 2.0.1`, and that version decorates `util.getLoop()` with `@functools.cache`. So `util.getLoop.cache_clear()` should stay in the reconnect paths until you upgrade `ib_async` and re-verify the behavior.
- `/gateway/status` in the current MCP server checks only raw TCP reachability to the gateway. It must not be treated as sufficient readiness once the MCP reconnection rewrite lands.

## Known Issues

### 1. Paper gateway auth expired silently (4 days undetected)

**What happened**: Paper gateway pod showed `Running 0/1` (Ready=False) since 2026-03-28 with `Unrecognized Username or Password`. The container kept running (IBC process alive) but couldn't authenticate. No alert fired.

**Root cause**: IBKR paper trading session expired or was disabled server-side. Required manual re-activation in IBKR Account Management portal.

**Fix applied**: Re-enabled paper trading in IBKR portal, restarted pod. Authenticated as DU4502670 (Simulated Trading).

**Prevention needed**: Readiness-based alert — if gateway pod shows Ready=False for >30 minutes during market hours (9:30 AM - 4:00 PM ET weekdays), send notification.

### 2. Live gateway requires manual 2FA on every restart

**What happens**: Live gateway restart → IBC attempts login → IBKR requests Second Factor Authentication → blocks until approved on IBKR mobile app (IB Key). If not approved within timeout, IBC retries (TWOFA_TIMEOUT_ACTION=restart).

**Impact**: Every live gateway restart (including daily AUTO_RESTART at 6 AM) requires human intervention if 2FA is triggered. In practice, IBKR remembers the device for a period, so 2FA isn't always required — but after a pod restart on a new IP or after extended downtime, it will be.

**Prevention**: No automated fix — IBKR requires 2FA for live accounts. Consider:
- Setting up IBKR's "Trusted IPs" if the cluster has a stable egress IP
- Using IBKR's SLS (Seamless Login System) if eligible
- Monitoring: alert if live gateway Ready=False for >5 minutes (2FA timeout)

### 3. "Login Messages" dialog causes re-login loop and drops API connections

**What happens**: After successful authentication, IBC encounters a "Login Messages" bulletin dialog from IBKR. IBC has **no handler** for this dialog (confirmed by IBC source code — 28 registered WindowHandlers, none for "Login Messages"). The dialog stays open. Combined with `ExistingSessionDetectedAction=primaryoverride`, IBC misinterprets the state and starts re-login attempts, dropping API client connections (`remove Client XXXXX` in logs).

**Impact**: NOT cosmetic — actively breaks `get_options_chain`, `get_contract_details`, and any call requiring sustained connection to the gateway. Only `get_historical_bars` survives because it uses a simpler request path. This blocks options implied move calculation for the predictor.

**Root cause (from IBC source)**: IBC's complete handler list (IbcTws.java lines 304-345) has no `LoginMessagesHandler` or `BulletinHandler`. The dialog falls through to `TwsListener.logWindowStructure()` as unrecognized.

**Fix (two parts)**:

1. **Change `ExistingSessionDetectedAction` from `primaryoverride` to `primary`** on live gateway. This prevents the re-login loop — the gateway holds its session and never yields to incoming sessions.

```bash
# In the deployment env vars:
EXISTING_SESSION_DETECTED_ACTION=primary  # was: primaryoverride
```

2. **Auto-dismiss "Login Messages" via xdotool** post-login. Since the gateway runs inside Xvfb, xdotool can find and close the unhandled dialog:

```bash
# Add as a post-startup script or init container
sleep 30 && xdotool search --name "Login Messages" windowactivate --sync key alt+F4 2>/dev/null || true
```

Alternatively, if using `gnzsnz/ib-gateway-docker` or `extrange/ibkr-docker` images, use the `IBC_SCRIPTS` env var to point to a directory with a post-login script that runs the xdotool command.

**Complete IBC config for unattended operation** (apply via env vars with `IBC_` prefix on extrange/ibkr image, or in config.ini directly):

```ini
ExistingSessionDetectedAction=primary
AcceptIncomingConnectionAction=accept
AcceptNonBrokerageAccountWarning=yes
AcceptBidAskLastSizeDisplayUpdateNotification=accept
ReloginAfterSecondFactorAuthenticationTimeout=yes
DismissNSEComplianceNotice=yes
SuppressInfoMessages=yes
CommandServerPort=7462
ControlFrom=0.0.0.0
BindAddress=0.0.0.0
```

### 4. `get_price` returns null — no live market data subscription

**What happens**: `mcp__ibkr-*__get_price` and `get_tickers` return null for all fields. The live account (U5113348) has **no market data subscription**. This is a paid IBKR add-on, not a code bug.

**Workaround**: Use `get_historical_bars` with `from_date`/`to_date` — this uses IBKR's free historical data service and works reliably for both live and paper.

**Note**: `get_historical_bars` returns end-of-bar data. For intraday, use `bar_size` of `1 min` or `5 mins`.

### 4b. Options chain / contract qualification fails — gateway connection drops

**What happens**: `get_options_chain` and `get_contract_details` return `'NoneType' object is not iterable`. The IB API call `reqSecDefOptParamsAsync` is a 24/7 contract metadata request — it does NOT require market hours. The failure is caused by the gateway dropping API connections (see issue #3 — Login Messages dialog).

**Evidence**: `remove Client XXXXX` in gateway logs immediately before/after the call. The API server connects, the gateway accepts, then the Login Messages re-login loop drops the client.

**Impact**: Cannot fetch options chain for implied move calculation. This blocks the predictor's ability to assess market-expected move magnitude.

**Fix**: Same as issue #3 — dismiss the Login Messages dialog. Once the gateway maintains a stable connection, options chain works 24/7 including after hours.

### 5. AUTO_RESTART_TIME cannot be weekly

**Current setting**: Paper is currently set to `AUTO_RESTART_TIME=06:00 AM`. Live logs on 2026-04-01 show `AutoRestartTime=` blank, so the live deployment still needs to be aligned to the intended schedule.

**Why daily**: IBKR forces daily disconnects on all gateway clients (~11:45 PM ET server reset). The AUTO_RESTART proactively re-authenticates before the forced disconnect. Without it, the gateway disconnects unpredictably during IBKR's maintenance window.

**Cannot change to weekly**: This is an IBKR platform requirement. The daily restart is the workaround, not the problem.

### 6. MCP session breaks after pod restart

**What happens**: When gateway/API pods are restarted, Claude Code's MCP tool connections become stale. Tool calls return `Invalid request parameters` or `MCP error -32602`.

**Fix**: Start a new Claude Code session after pod restarts. MCP connections are per-session and don't survive pod restarts.

**Future improvement**: MCP server could implement reconnection logic or Claude Code could detect stale connections and re-initialize.

## Monitoring Wishlist (TODO)

1. **Alert: Gateway Ready=False during market hours** — check every 5 minutes, alert after 30 min continuous failure
2. **Alert: API server can't connect to gateway** — check `Connection refused` in API server logs
3. **Dashboard: Gateway auth status** — Grafana panel showing last successful login time per gateway
4. **Automated paper re-activation check** — periodic test trade or price fetch, alert on failure

## Quick Reference

**Restart paper gateway:**
```bash
kubectl -n mcp-services rollout restart deployment ibkr-paper-gateway
kubectl -n mcp-services rollout restart deployment ibkr-paper  # MCP server too
```

**Restart live gateway (requires 2FA approval on phone):**
```bash
kubectl -n mcp-services rollout restart deployment ibkr-ib-gateway
kubectl -n mcp-services rollout restart deployment ibkr  # MCP server too
```

**Check gateway auth:**
```bash
kubectl -n mcp-services logs -l app.kubernetes.io/name=ibkr-ib-gateway --tail=5
kubectl -n mcp-services logs -l app.kubernetes.io/name=ibkr-paper-gateway --tail=5
```

**Check credentials:**
```bash
kubectl -n mcp-services get secret ibkr-credentials -o jsonpath='{.data.username}' | base64 -d
```

**Accounts:**
- Live: U5113348
- Paper: DU4502670

---

## Implementation Plan — IBKR Reliability Hardening

**Created**: 2026-04-01
**Status**: DRAFT — awaiting approval before implementation
**Scope**: 3 phases — K8s manifests, MCP server code, monitoring
**Principle**: Paper = auto-restart aggressively. Live = alert-don't-restart (restart = 2FA).

### Research Summary

Exhaustive research across 13+ IBKR MCP GitHub repos, Reddit, HN, Elite Trader, IBC issue tracker, and deep code analysis of `omdv/ibkr-mcp-server` confirms:

- **No 100% unattended Live exists** — IBKR requires 2FA for retail live accounts on every cold restart. No library, Docker image, or MCP server eliminates this.
- **Current stack is the right foundation**: `gnzsnz/ib-gateway` (887 stars, most maintained) + `omdv/ibkr-mcp-server` (uses `ib_async`, only project with K8s Helm charts) + separate Live/Paper deployments.
- **Don't switch to Web API** — even `rcontesti/IB_MCP` (105 stars, the most popular CP-based MCP) says TWS API is faster and more reliable for trading.
- **The reliability gap is in two layers**: (1) IBC config allows the Login Messages dialog to crash connections, and (2) the MCP server has zero reconnection logic.

### CRITICAL FINDING: Helm Chart vs Running State Mismatch

**Verified empirically on 2026-04-01 from the running cluster.**

The Helm chart on disk (`ibkr-mcp-server/chart/templates/`) is **broken for gnzsnz/ib-gateway**. The live gateway currently works because it was **manually patched** post-deploy. A naive `helm upgrade` would **destroy the working config**.

#### Evidence

**gnzsnz/ib-gateway `config.ini.tmpl` uses these env vars** (verified: `kubectl exec` → `cat config.ini.tmpl`):
```
${TWS_USERID}, ${TWS_PASSWORD}, ${TRADING_MODE}, ${EXISTING_SESSION_DETECTED_ACTION},
${READ_ONLY_API}, ${AUTO_RESTART_TIME}, ${RELOGIN_AFTER_TWOFA_TIMEOUT},
${TWS_ACCEPT_INCOMING}, ${TWS_COLD_RESTART}, ${TWOFA_TIMEOUT_ACTION}
```
The image uses `envsubst` to substitute these into `config.ini`. It has **zero code** that processes `IBC_*` prefixed env vars.

**Helm chart renders** (verified: `helm get manifest ibkr`):
```yaml
env:
- name: USERNAME          # ← WRONG: gnzsnz expects TWS_USERID
- name: PASSWORD          # ← WRONG: gnzsnz expects TWS_PASSWORD
envFrom:
- configMapRef: ibkr-config  # ← contains IBC_TradingMode, IBC_ExistingSessionDetectedAction, etc.
                              #    gnzsnz IGNORES all IBC_* vars
```

**Actually running deployment** (verified: `kubectl get deployment ibkr-ib-gateway -o jsonpath`):
```yaml
env:
- name: TWS_USERID        # ← CORRECT: manually patched
- name: TWS_PASSWORD       # ← CORRECT: manually patched
- name: TRADING_MODE       # ← CORRECT: "live"
- name: READ_ONLY_API      # ← CORRECT: "no"
- name: EXISTING_SESSION_DETECTED_ACTION  # ← "primaryoverride" (needs fix to "primary")
- name: TWOFA_TIMEOUT_ACTION              # ← "restart" (correct)
- name: RELOGIN_AFTER_TWOFA_TIMEOUT      # ← "yes" (correct)
- name: VNC_SERVER_PASSWORD               # ← "ibkr123"
# NO envFrom — configmap completely bypassed
```

**Rendered config.ini inside running live container** (verified: `kubectl exec` → `grep config.ini`):
```ini
TradingMode=live                              # from TRADING_MODE=live (direct env var)
ExistingSessionDetectedAction=primaryoverride  # from EXISTING_SESSION_DETECTED_ACTION (direct env var)
ReadOnlyApi=no                                # from READ_ONLY_API=no (direct env var)
AutoRestartTime=                              # EMPTY — no AUTO_RESTART_TIME env var set!
AcceptIncomingConnectionAction=               # EMPTY — no TWS_ACCEPT_INCOMING env var set!
CommandServerPort=0                           # ZERO — no IBC command port!
ControlFrom=                                  # EMPTY
BindAddress=                                  # EMPTY
SuppressInfoMessages=yes                      # hardcoded in template
DismissNSEComplianceNotice=yes                # hardcoded in template
```

#### What this means

| Setting | Helm chart would set | Actually running | Impact |
|---------|---------------------|-----------------|--------|
| Credentials | `USERNAME`/`PASSWORD` (wrong) | `TWS_USERID`/`TWS_PASSWORD` (correct) | Helm upgrade = auth failure |
| Trading mode | `IBC_TradingMode=paper` (ignored) | `TRADING_MODE=live` (correct) | Helm upgrade = paper mode on live! |
| ReadOnly | `IBC_ReadOnlyApi=yes` (ignored) | `READ_ONLY_API=no` (correct) | Helm upgrade = read-only orders |
| Session action | `IBC_ExistingSessionDetectedAction` (ignored) | `EXISTING_SESSION_DETECTED_ACTION` (works) | — |
| AutoRestart | `IBC_AutoRestartTime` (ignored) | **NOT SET** (empty in config.ini) | Live has NO daily auto-restart! |
| CommandServer | `IBC_CommandServerPort=7462` (ignored) | **PORT=0** (disabled) | IBC commands unreachable |
| ControlFrom | `IBC_ControlFrom=0.0.0.0` (ignored) | **EMPTY** (localhost default) | IBC commands blocked |

**Three things are silently broken on the live gateway right now:**
1. `AUTO_RESTART_TIME` is empty → no daily proactive re-auth → gateway relies on IB's forced disconnect + K8s restart
2. `CommandServerPort=0` → IBC command server disabled → `send_command_to_ibc("RESTART")` in MCP server code does nothing
3. `AcceptIncomingConnectionAction` is empty → IBC uses default (which prompts interactively — but in headless Xvfb, the prompt hangs)

### Currently Running

```
Gateway image: ghcr.io/gnzsnz/ib-gateway:stable
  Digest:      sha256:b1d2684203cbf0f1c1d57c782872716727e0721c344dcee74f4d8fb1b8d13573

MCP image:     ghcr.io/omdv/ibkr-mcp-server:latest
  Digest:      sha256:f5ad0af29ff67f317ad2b26194c5bdd9f70774fdeba83279a97efaf4d16cb445

Node:          minisforum (all 4 pods)
PVCs:          none (JTS home is ephemeral)
Live liveness: none (correct — don't auto-kill live)
Live readiness: tcpSocket:4001, period=30s, failure=3
```

---

### Phase 0: Fix the Helm Chart (MUST DO FIRST)

**Goal**: Rewrite the Helm chart to use gnzsnz/ib-gateway's actual env var contract, then sync the running state with the chart so `helm upgrade` is safe.

#### 0A. Rewrite the Helm gateway env vars to gnzsnz format

The Helm chart was written for `extrange/ibkr-docker` env var naming (`IBC_*` prefix, `USERNAME`/`PASSWORD`), but we run `gnzsnz/ib-gateway` which uses UPPER_SNAKE_CASE without prefix and `TWS_USERID`/`TWS_PASSWORD`.

**File**: `k8s/mcp-services/ibkr-values.yaml` — replace the `config:` section entirely:

```yaml
# BEFORE (entire config block, lines 51-64):
config:
  twoFaTimeoutAction: "restart"
  ibcTradingMode: "live"
  ibcReadOnlyApi: "yes"
  ibcReloginAfterSecondFactorAuthenticationTimeout: "yes"
  ibcAutoRestartTime: "06:00 AM"
  ibcColdRestartTime: "10:00"
  ibcExistingSessionDetectedAction: "primaryoverride"
  ibcAcceptIncomingConnectionAction: "accept"
  ibcAcceptBidAskLastSizeDisplayUpdateNotification: "defer"
  ibcCommandServerPort: "7462"
  ibcControlFrom: "127.0.0.1"
  ibcBindAddress: "127.0.0.1"
  ibkrLogLevel: "INFO"
  corsAllowedOrigins: "*"
  enableMcp: "true"

# AFTER — split into gateway config (gnzsnz format) and MCP server config:
gatewayConfig:
  # gnzsnz/ib-gateway env vars (UPPER_SNAKE_CASE, no IBC_ prefix)
  tradingMode: "live"
  readOnlyApi: "no"
  twofaTimeoutAction: "restart"
  reloginAfterTwofaTimeout: "yes"
  existingSessionDetectedAction: "primary"       # was: primaryoverride (fix for Issue #3)
  autoRestartTime: "06:00 AM"                     # was: empty (silently broken!)
  coldRestartTime: "10:00"
  acceptIncoming: "accept"                        # was: empty (silently broken!)
  vncPassword: "ibkr123"
  # CommandServerPort, ControlFrom, BindAddress — hardcoded in gnzsnz template, not configurable

mcpConfig:
  # omdv/ibkr-mcp-server env vars (IBKR_ prefix)
  logLevel: "INFO"
  corsAllowedOrigins: "*"
  enableMcp: "true"
```

**File**: `ibkr-mcp-server/chart/templates/ib-gateway-deployment.yaml` — replace env section:

```yaml
# BEFORE:
        env:
        - name: USERNAME
          valueFrom:
            secretKeyRef:
              name: {{ include "ibkr.gatewaySecretName" . }}
              key: username
        - name: PASSWORD
          valueFrom:
            secretKeyRef:
              name: {{ include "ibkr.gatewaySecretName" . }}
              key: password
        envFrom:
        - configMapRef:
            name: {{ include "ibkr.fullname" . }}-config

# AFTER — direct env vars using gnzsnz naming:
        env:
        - name: TWS_USERID
          valueFrom:
            secretKeyRef:
              name: {{ include "ibkr.gatewaySecretName" . }}
              key: username
        - name: TWS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: {{ include "ibkr.gatewaySecretName" . }}
              key: password
        - name: TRADING_MODE
          value: {{ .Values.gatewayConfig.tradingMode | quote }}
        - name: READ_ONLY_API
          value: {{ .Values.gatewayConfig.readOnlyApi | quote }}
        - name: TWOFA_TIMEOUT_ACTION
          value: {{ .Values.gatewayConfig.twofaTimeoutAction | quote }}
        - name: RELOGIN_AFTER_TWOFA_TIMEOUT
          value: {{ .Values.gatewayConfig.reloginAfterTwofaTimeout | quote }}
        - name: EXISTING_SESSION_DETECTED_ACTION
          value: {{ .Values.gatewayConfig.existingSessionDetectedAction | quote }}
        - name: AUTO_RESTART_TIME
          value: {{ .Values.gatewayConfig.autoRestartTime | quote }}
        - name: TWS_COLD_RESTART
          value: {{ .Values.gatewayConfig.coldRestartTime | quote }}
        - name: TWS_ACCEPT_INCOMING
          value: {{ .Values.gatewayConfig.acceptIncoming | quote }}
        - name: ACCEPT_NON_BROKERAGE_ACCOUNT_WARNING
          value: "yes"
        - name: VNC_SERVER_PASSWORD
          value: {{ .Values.gatewayConfig.vncPassword | quote }}
        # CommandServerPort, ControlFrom, BindAddress, SuppressInfoMessages,
        # DismissNSEComplianceNotice, AcceptBidAskLastSizeDisplayUpdateNotification
        # are HARDCODED in the gnzsnz config.ini template — not configurable via env vars.
        # CommandServerPort=0 (disabled). IBC commands won't work; use kubectl instead.
        # DO NOT use envFrom — gateway and MCP server have different env contracts
```

> **VERIFIED**: `CommandServerPort`, `ControlFrom`, `BindAddress`, `SuppressInfoMessages`, `DismissNSEComplianceNotice`, and `AcceptBidAskLastSizeDisplayUpdateNotification` are **hardcoded in the gnzsnz template** — NOT configurable via env vars. Setting `IBC_ControlFrom=0.0.0.0` as an env var does nothing. Specifically:
> - `CommandServerPort=0` (disabled) — the IBC command server is OFF by design in gnzsnz
> - `SuppressInfoMessages=yes` — already hardcoded (no env var needed)
> - `DismissNSEComplianceNotice=yes` — already hardcoded
> - `AcceptBidAskLastSizeDisplayUpdateNotification=accept` — already hardcoded
>
> **Impact**: The MCP server's `send_command_to_ibc("RESTART")` in `market_data.py:99` **will never work** with this image. Gateway restarts must be done via `kubectl rollout restart`, not IBC commands. The MCP server code that sends IBC commands should be removed or replaced with a K8s API call.
>
> To enable the IBC command server, you'd need `CUSTOM_CONFIG=yes` + a mounted custom `config.ini` (losing all envsubst templating), or a post-start sed script. Not recommended — `kubectl` restart is more reliable anyway.

**File**: `ibkr-mcp-server/chart/templates/configmap.yaml` — reduce to MCP-only config:

```yaml
# BEFORE (mixed gateway + MCP vars):
data:
  TWOFA_TIMEOUT_ACTION: ...
  GATEWAY_OR_TWS: "gateway"
  IBC_TradingMode: ...
  # ... 13 more IBC_* vars ...
  IBKR_GATEWAY_MODE: "external"
  IBKR_IB_GATEWAY_HOST: ...
  # ... MCP vars ...

# AFTER — MCP server vars only:
data:
  IBKR_GATEWAY_MODE: "external"
  IBKR_IB_GATEWAY_HOST: {{ include "ibkr.fullname" . }}-ib-gateway
  IBKR_IB_GATEWAY_PORT: "4003"
  IBKR_APPLICATION_HOST: "0.0.0.0"
  IBKR_APPLICATION_PORT: "8000"
  IBKR_LOG_LEVEL: {{ .Values.mcpConfig.logLevel | quote }}
  IBKR_ENABLE_MCP: {{ .Values.mcpConfig.enableMcp | quote }}
```

> **Port note**: this live chart must point the MCP server at the actual live gateway service port (`4003`). Paper is separate and already uses `4004` in `k8s/mcp-services/ibkr-paper-mcp.yaml`.

#### 0B. Verify gnzsnz template variables for IBC command server

Need to confirm the exact env var names for CommandServerPort, ControlFrom, BindAddress in the gnzsnz template. The rendered config.ini shows these as empty/zero, meaning the current env vars don't match.

```bash
# Run this to get the definitive mapping:
kubectl -n mcp-services exec deployment/ibkr-ib-gateway -- \
  grep -E '(CommandServer|ControlFrom|BindAddress)' /home/ibgateway/ibc/config.ini.tmpl
```

If the template uses literal values (not `${VAR}` substitution), we need to mount a custom config.ini instead of relying on env vars.

#### 0C. Sync paper gateway to same convention

The paper gateway (`k8s/mcp-services/ibkr-paper-gateway.yaml`) already uses the correct gnzsnz format (`TRADING_MODE`, `TWS_USERID`, etc.) but is missing several vars. Add the missing ones:

**File**: `k8s/mcp-services/ibkr-paper-gateway.yaml` — add missing env vars:
```yaml
        # ADD after existing env vars:
        - name: AUTO_RESTART_TIME
          value: "06:00 AM"
        - name: TWS_ACCEPT_INCOMING
          value: "accept"
        - name: DISMISS_NSE_COMPLIANCE_NOTICE
          value: "yes"
```

> **NOTE**: `SUPPRESS_INFO_MESSAGES` is already hardcoded in the `gnzsnz` template, so adding it as an env var here would be ignored.

> **NOTE**: Paper gateway already has `EXISTING_SESSION_DETECTED_ACTION=secondary` which is correct for paper (yields to live session).

---

### Phase 1: K8s Manifest Hardening (Gateway Layer)

**Goal**: Eliminate the Login Messages re-login loop, prevent surprise image pulls, persist gateway state across restarts, and split Live/Paper restart policies.

**PREREQUISITE**: Phase 0 must be complete so that `helm upgrade` is safe.

#### 1A. Pin image digests (both gateways + both MCP servers)

**Why**: Floating `stable`/`latest` tags can pull breaking changes on pod restart. Pin to the exact digests currently running.

**File**: `k8s/mcp-services/ibkr-values.yaml`
```yaml
ibGateway:
  image:
    repository: ghcr.io/gnzsnz/ib-gateway
    tag: "stable@sha256:b1d2684203cbf0f1c1d57c782872716727e0721c344dcee74f4d8fb1b8d13573"
    pullPolicy: IfNotPresent

mcpServer:
  image:
    repository: ghcr.io/omdv/ibkr-mcp-server
    tag: "latest@sha256:f5ad0af29ff67f317ad2b26194c5bdd9f70774fdeba83279a97efaf4d16cb445"
    pullPolicy: IfNotPresent
```

**File**: `k8s/mcp-services/ibkr-paper-gateway.yaml`
```yaml
        image: ghcr.io/gnzsnz/ib-gateway:stable@sha256:b1d2684203cbf0f1c1d57c782872716727e0721c344dcee74f4d8fb1b8d13573
```

**File**: `k8s/mcp-services/ibkr-paper-mcp.yaml`
```yaml
        image: ghcr.io/omdv/ibkr-mcp-server:latest@sha256:f5ad0af29ff67f317ad2b26194c5bdd9f70774fdeba83279a97efaf4d16cb445
```

#### 1B. xdotool-based Login Messages dismissal via `IBC_SCRIPTS`

**Why**: IBC has no handler for the "Login Messages" bulletin dialog (28 handlers, none match). xdotool running in a loop can find and dismiss it. The `gnzsnz/ib-gateway` image supports post-login scripts via `IBC_SCRIPTS` env var, but the base image itself does **not** ship with `xdotool`.

**Preferred approach**: Use gnzsnz's built-in `IBC_SCRIPTS` mechanism instead of a sidecar, but pair it with a **thin derived image** that adds `xdotool`. This keeps the dismissal loop in the SAME container with access to the X display and avoids unverified cross-container X11 assumptions.

**File**: `docker/ibkr-gateway-xdotool/Dockerfile` (NEW)
```dockerfile
FROM ghcr.io/gnzsnz/ib-gateway:10.37.1q

USER root
RUN apt-get update \
 && apt-get install --no-install-recommends -y xdotool \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

USER 1000:1000
```

**File**: `k8s/mcp-services/ibkr-login-dismiss-cm.yaml` (NEW)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ibkr-login-dismiss-script
  namespace: mcp-services
data:
  dismiss-login-messages.sh: |
    #!/bin/bash
    # Dismiss the "Login Messages" dialog that IBC can't handle.
    # Called by gnzsnz/ib-gateway via IBC_SCRIPTS after login.
    # IMPORTANT: gnzsnz run_scripts() is synchronous, so this script must
    # self-background or gateway startup will hang.
    (
      sleep 30
      echo "[dismiss] Starting Login Messages dismisser (DISPLAY=$DISPLAY)"
      while true; do
        for TITLE in "Login Messages" "Important Notice" "Bulletin" "TWS Message"; do
          WID=$(xdotool search --name "$TITLE" 2>/dev/null | head -1)
          if [ -n "$WID" ]; then
            echo "[dismiss] Found '$TITLE' dialog (WID=$WID), closing..."
            xdotool windowactivate --sync "$WID" key alt+F4 2>/dev/null || \
            xdotool windowactivate --sync "$WID" key Return 2>/dev/null
            echo "[dismiss] Dismissed '$TITLE' at $(date)"
            sleep 2
          fi
        done
        sleep 10
      done
    ) &
```

**File**: Helm gateway deployment — add volume mount + `IBC_SCRIPTS` env var:
```yaml
        # ADD to gateway container env:
        - name: IBC_SCRIPTS
          value: "ibc-scripts"
        # ADD volumeMount:
        volumeMounts:
        - name: dismiss-script
          mountPath: /home/ibgateway/ibc-scripts

      # ADD to pod volumes:
      volumes:
      - name: dismiss-script
        configMap:
          name: ibkr-login-dismiss-script
          defaultMode: 0755
```

> **NOTE**: `IBC_SCRIPTS` must be a path relative to `$HOME`; `gnzsnz` resolves it as `"$HOME/$IBC_SCRIPTS"`.

**File**: `k8s/mcp-services/ibkr-paper-gateway.yaml` — same pattern for paper.

#### 1C. Persist Live gateway state via `TWS_SETTINGS_PATH`

**Why**: IB Gateway stores session state, auth tokens, and settings in `~/Jts/`. Without persistence, every pod restart loses this state and may require fresh 2FA. A PVC preserves auth cookies so the daily AUTO_RESTART can re-authenticate without 2FA.

**File**: `k8s/mcp-services/ibkr-jts-pvc.yaml` (NEW)
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ibkr-live-jts-home
  namespace: mcp-services
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: local-path
  resources:
    requests:
      storage: 1Gi
```

**File**: Helm gateway deployment — prefer upstream-supported `TWS_SETTINGS_PATH` persistence instead of mounting the whole `Jts` tree:
```yaml
        env:
        - name: TWS_SETTINGS_PATH
          value: /home/ibgateway/tws_settings

        volumeMounts:
        - name: tws-settings
          mountPath: /home/ibgateway/tws_settings

      volumes:
      - name: tws-settings
        persistentVolumeClaim:
          claimName: ibkr-live-jts-home
```

> **NOTE**: This follows the upstream `gnzsnz/ib-gateway` recommendation. Mounting the entire `/home/ibgateway/Jts` directory is a fallback, but `TWS_SETTINGS_PATH` is the cleaner persistence path. Paper does NOT get a PVC — it restarts aggressively and paper 2FA is not required.

#### 1D. Live vs Paper probe asymmetry

**Current state** (confirmed from running cluster):
- Live gateway: NO liveness probe, readiness on TCP 4001 ← **correct, keep as-is**
- Paper gateway: NO liveness probe, readiness on TCP 4002

**Change for Paper only**: Add aggressive liveness probe.

**File**: `k8s/mcp-services/ibkr-paper-gateway.yaml`
```yaml
        livenessProbe:
          tcpSocket:
            port: 4002
          initialDelaySeconds: 300
          periodSeconds: 60
          failureThreshold: 5
          timeoutSeconds: 5
```

**Do NOT add a liveness probe to the live gateway.** Restart = 2FA.

---

### Phase 2: MCP Server Reconnection Logic (Application Layer)

**Goal**: Replace the per-request lazy connect with a long-lived, self-healing IB connection that survives daily gateway restarts.

#### 2A. Rewrite `client.py` — long-lived connection with disconnectedEvent + heartbeat

**Why**: Current `_connect()` (line 25) creates a new connection on every request if disconnected, uses a random clientId, has no retry/backoff, no heartbeat, and no `disconnectedEvent` handler. When the gateway restarts (daily 6 AM), the MCP server silently holds a dead connection until the next request.

**File**: `ibkr-mcp-server/app/services/client.py` — full replacement:

```python
"""Base IB client connection handling — long-lived, self-healing."""

import asyncio
import datetime as dt
import exchange_calendars as ecals
from ib_async import IB, util

from app.core.config import get_config
from app.core.setup_logging import logger

# Fixed client IDs avoid collisions with OrderClient (clientId=1)
MARKET_DATA_CLIENT_ID = 10


class IBClient:
    """Base IB client with long-lived connection, heartbeat, and auto-reconnect."""

    def __init__(self) -> None:
        self.config = get_config()
        self.ib = IB()
        self._contract_cache: dict[tuple[str, str, str, str], object] = {}
        self._reconnect_lock = asyncio.Lock()
        self._heartbeat_task: asyncio.Task | None = None
        self._connected_event = asyncio.Event()
        self._shutting_down = False

        # Wire up disconnect handler
        self.ib.disconnectedEvent += self._on_disconnected

    def _on_disconnected(self) -> None:
        """Called by ib_async when the gateway connection drops."""
        self._connected_event.clear()
        if self._shutting_down:
            logger.info("IB disconnected (shutdown)")
            return
        logger.warning("IB connection lost — scheduling reconnect")
        # Schedule reconnect in the background (can't await in sync callback)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._reconnect_with_backoff())
        except RuntimeError:
            logger.error("No running event loop for reconnect scheduling")

    async def _reconnect_with_backoff(self) -> None:
        """Reconnect with exponential backoff. Max 5 attempts, then wait 60s and retry."""
        async with self._reconnect_lock:
            if self.ib.isConnected():
                self._connected_event.set()
                return

            delays = [1, 2, 5, 10, 30]  # seconds
            for attempt, delay in enumerate(delays, 1):
                try:
                    logger.info(
                        "Reconnect attempt {}/{} (waiting {}s)...",
                        attempt, len(delays), delay,
                    )
                    await asyncio.sleep(delay)

                    if hasattr(util.getLoop, "cache_clear"):
                        util.getLoop.cache_clear()

                    # Disconnect cleanly first if in bad state
                    if self.ib.isConnected():
                        self.ib.disconnect()

                    await self.ib.connectAsync(
                        host=self.config.ib_gateway_host,
                        port=self.config.ib_gateway_port,
                        clientId=MARKET_DATA_CLIENT_ID,
                        timeout=20,
                        readonly=False,
                    )
                    self.ib.RequestTimeout = 20
                    self._connected_event.set()
                    self._contract_cache.clear()  # stale after reconnect
                    logger.info("Reconnected to IB gateway on attempt {}", attempt)
                    return
                except Exception as e:
                    logger.warning("Reconnect attempt {} failed: {}", attempt, e)

            # All attempts exhausted — wait 60s and try once more
            logger.error("All reconnect attempts failed. Waiting 60s for final try...")
            await asyncio.sleep(60)
            try:
                if hasattr(util.getLoop, "cache_clear"):
                    util.getLoop.cache_clear()
                if self.ib.isConnected():
                    self.ib.disconnect()
                await self.ib.connectAsync(
                    host=self.config.ib_gateway_host,
                    port=self.config.ib_gateway_port,
                    clientId=MARKET_DATA_CLIENT_ID,
                    timeout=20,
                    readonly=False,
                )
                self.ib.RequestTimeout = 20
                self._connected_event.set()
                self._contract_cache.clear()
                logger.info("Reconnected on final attempt")
            except Exception as e:
                logger.error("Final reconnect failed: {}. Will retry on next request.", e)

    async def _connect(self) -> None:
        """Ensure connection is alive. Uses existing connection if healthy."""
        if self.ib.isConnected():
            return

        # If a reconnect is in progress, wait for it
        if self._reconnect_lock.locked():
            logger.debug("Waiting for in-progress reconnect...")
            try:
                await asyncio.wait_for(self._connected_event.wait(), timeout=90)
            except asyncio.TimeoutError:
                raise ConnectionError("Timed out waiting for IB reconnect") from None
            return

        # First connect or reconnect needed
        await self._reconnect_with_backoff()
        if not self.ib.isConnected():
            raise ConnectionError("Failed to connect to IB gateway")

    async def start_heartbeat(self) -> None:
        """Start periodic heartbeat to detect dead connections proactively.

        Call this from the FastAPI lifespan after initial connection.
        """
        if self._heartbeat_task is not None:
            return
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("IB heartbeat started (30s interval)")

    async def _heartbeat_loop(self) -> None:
        """Ping IB gateway every 30s with reqCurrentTime. If it fails, trigger reconnect."""
        while not self._shutting_down:
            await asyncio.sleep(30)
            if not self.ib.isConnected():
                continue  # reconnect handler is already working
            try:
                t = await asyncio.wait_for(
                    self.ib.reqCurrentTimeAsync(),
                    timeout=10,
                )
                logger.debug("Heartbeat OK — IB server time: {}", t)
            except Exception as e:
                logger.warning("Heartbeat failed: {} — triggering reconnect", e)
                self.ib.disconnect()  # will fire disconnectedEvent → auto-reconnect

    async def _qualify_contract(
        self,
        symbol: str,
        sec_type: str,
        exchange: str,
        currency: str,
    ) -> object:
        """Return a qualified Contract, using a cache to avoid redundant IB round-trips."""
        from ib_async.contract import Contract

        key = (symbol.upper(), sec_type.upper(), exchange.upper(), currency.upper())
        if key not in self._contract_cache:
            contract = Contract(
                symbol=symbol,
                secType=sec_type,
                exchange=exchange,
                currency=currency,
            )
            [qualified] = await self.ib.qualifyContractsAsync(contract)
            self._contract_cache[key] = qualified
            logger.debug(
                "Qualified contract {}/{} conId={}",
                symbol, exchange, self._contract_cache[key].conId,
            )
        return self._contract_cache[key]

    def _is_market_open(self) -> bool:
        """Return True if the NYSE is currently in a trading minute (UTC)."""
        nyse = ecals.get_calendar("NYSE")
        return nyse.is_trading_minute(dt.datetime.now(dt.UTC))

    async def send_command_to_ibc(self, command: str) -> None:
        """Send a command to the IBC Command Server."""
        if not command:
            logger.error("Error: you must supply a valid IBC command")
            return

        host = self.config.ib_gateway_host
        port = self.config.ib_command_server_port

        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.write(command.encode() + b"\n")
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            logger.debug("Successfully sent command to IBC: {}", command)
        except Exception as e:
            logger.error("Error sending command to IBC: {}", str(e))
            raise

    async def shutdown(self) -> None:
        """Graceful shutdown — stop heartbeat and disconnect."""
        self._shutting_down = True
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        if self.ib.isConnected():
            self.ib.disconnect()

    def __del__(self) -> None:
        """Disconnect from IB."""
        try:
            if self.ib and self.ib.isConnected():
                self.ib.disconnect()
        except Exception:
            pass
```

> **NOTE**: Keep `send_command_to_ibc()` only if you later enable the IBC command server deliberately. In the current `gnzsnz` setup it is disabled by default, so this method should not be used by normal request paths and can be removed entirely if you want the leanest implementation.

**Key changes from current code**:
1. **Fixed clientId=10** instead of random — avoids collisions, enables reconnect to same session
2. **`disconnectedEvent` handler** — auto-triggers reconnect when gateway drops
3. **Exponential backoff** — 1s, 2s, 5s, 10s, 30s, then 60s final attempt
4. **`util.getLoop.cache_clear()`** before reconnect attempts — needed for the repo's locked `ib-async 2.0.1`
5. **Heartbeat** every 30s via `reqCurrentTime()` — detects dead connections proactively
6. **`_reconnect_lock`** — prevents concurrent reconnect storms
7. **Contract cache cleared on reconnect** — stale conIds can cause errors
8. **Graceful shutdown** — stops heartbeat, disconnects cleanly

#### 2B. Fix market data type — delayed fallback should use type 4 (delayed-frozen), not 2 (frozen)

**Why**: `reqMarketDataType(2)` requests "frozen" data — the last snapshot before market close. `reqMarketDataType(3)` requests "delayed" data (15-min delayed feed, available without subscription). `reqMarketDataType(4)` requests "delayed-frozen" — delayed data when available, otherwise last frozen value. Type 3 or 4 is correct for after-hours when you lack a live subscription.

**File**: `ibkr-mcp-server/app/services/market_data.py`
```python
# BEFORE (lines 82-84):
      else:
        logger.debug("Market is closed, requesting delayed market data")
        self.ib.reqMarketDataType(2)

# AFTER:
      else:
        logger.debug("Market is closed, requesting delayed-frozen market data")
        self.ib.reqMarketDataType(4)  # delayed-frozen: best available without subscription
```

Apply the same change at lines 104-106 in the current retry branch. Long term, item 2F removes the inline restart path entirely:
```python
# BEFORE:
          self.ib.reqMarketDataType(2)

# AFTER:
          self.ib.reqMarketDataType(4)
```

Also in `history.py` `get_current_price()` (line 93):
```python
# BEFORE (line 93):
      self.ib.reqMarketDataType(1)

# AFTER — use type 4 as fallback, type 1 for live:
      self.ib.reqMarketDataType(1)  # unchanged — live path is correct
```
(The history.py live path is already correct; the closed path uses `reqHistoricalDataAsync` which doesn't need `reqMarketDataType`.)

#### 2C. Split liveness and readiness — process alive vs usable IB session

**Why**: Current `/health` endpoint (main.py:82) always returns `{"status": "ok"}` regardless of IB connection state. Also, the existing readiness path `/gateway/status` checks only raw TCP reachability to the gateway. After the reconnect rewrite, we need K8s to distinguish:

- Python process is alive
- MCP currently has a usable IB session

**File**: `ibkr-mcp-server/app/main.py`
```python
# ADD to imports:
import asyncio
from fastapi import FastAPI, Depends, HTTPException

# BEFORE (lines 82-85):
@app.get("/health", include_in_schema=False)
def health() -> dict:
  """Liveness check — proves the Python process is alive."""
  return {"status": "ok"}

# AFTER:
@app.get("/livez", include_in_schema=False)
def livez() -> dict:
  """K8s liveness: process is alive."""
  return {"status": "ok"}

@app.get("/readyz", include_in_schema=False)
async def readyz() -> dict:
  """K8s readiness: MCP has a usable IB session."""
  if not ib_interface or not ib_interface.ib.isConnected():
    raise HTTPException(status_code=503, detail="IB disconnected")

  try:
    await asyncio.wait_for(ib_interface.ib.reqCurrentTimeAsync(), timeout=5)
  except Exception as exc:
    raise HTTPException(status_code=503, detail=f"IB heartbeat failed: {exc}") from exc

  return {"status": "ok", "ib_connected": True}
```

> **NOTE**: Keep `/gateway/status` as a debug endpoint only. It is useful for diagnosing raw gateway reachability, but it is not a reliable readiness signal for the MCP process itself.

#### 2D. Wire heartbeat into FastAPI lifespan

**File**: `ibkr-mcp-server/app/main.py` — update the lifespan:

```python
# BEFORE lifespan (lines 16-32):
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
  """Lifespan events for the application."""
  logger.info("Starting IBKR MCP Server...")
  # ... gateway startup ...
  yield
  # Shutdown
  logger.info("Shutting down IBKR MCP Server...")
  try:
    await gateway.gateway_manager.cleanup()
  except Exception:
    logger.exception("Error during cleanup.")

# AFTER:
# Import IBInterface singleton at module level
from app.services.interfaces import IBInterface
ib_interface = IBInterface()

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
  """Lifespan events for the application."""
  logger.info("Starting IBKR MCP Server...")

  if not gateway.gateway_manager.is_external:
    try:
      success = await gateway.gateway_manager.start_gateway()
      if not success:
        logger.error("Failed to start internal IBKR Gateway.")
    except Exception:
      logger.exception("Error starting internal IBKR Gateway.")
  else:
    logger.info("External gateway mode - connection will be established on-demand")

  # Establish initial IB connection and start heartbeat
  try:
    await ib_interface._connect()
    await ib_interface.start_heartbeat()
    logger.info("IB connection established and heartbeat started")
  except Exception:
    logger.warning("Initial IB connection failed — will retry on first request")

  yield

  # Shutdown
  logger.info("Shutting down IBKR MCP Server...")
  await ib_interface.shutdown()
  try:
    await gateway.gateway_manager.cleanup()
  except Exception:
    logger.exception("Error during cleanup.")
```

> **NOTE**: The API route handlers currently create their own IBInterface instance. After this change, they should use the shared `ib_interface` singleton. This requires updating `ibkr-mcp-server/app/api/ibkr/__init__.py` or the individual route files to import from `app.main` or use a dependency injection pattern.

#### 2E. Apply similar reconnection to OrderClient

**File**: `ibkr-mcp-server/app/services/orders.py` — `_connect_orders()` needs the same treatment:

```python
# BEFORE (lines 43-57):
    async def _connect_orders(self) -> None:
        if self._order_ib.isConnected():
            return
        try:
            await self._order_ib.connectAsync(...)
        except Exception as e:
            logger.error("Error connecting order client: {}", e)
            raise

# AFTER — add retry with backoff:
    async def _connect_orders(self) -> None:
        if self._order_ib.isConnected():
            return

        delays = [1, 2, 5, 10, 30]
        for attempt, delay in enumerate(delays, 1):
            try:
                if attempt > 1:
                    await asyncio.sleep(delay)
                if hasattr(util.getLoop, "cache_clear"):
                    util.getLoop.cache_clear()
                await self._order_ib.connectAsync(
                    host=self._config.ib_gateway_host,
                    port=self._config.ib_gateway_port,
                    clientId=ORDER_CLIENT_ID,
                    timeout=20,
                    readonly=False,
                )
                self._order_ib.RequestTimeout = 20
                logger.info("Order connection established (clientId={}, attempt={})",
                            ORDER_CLIENT_ID, attempt)
                return
            except Exception as e:
                logger.warning("Order connect attempt {}/{} failed: {}",
                               attempt, len(delays), e)

        raise ConnectionError("Failed to connect order client after all retries")
```

Add `util` to the imports in `orders.py` as well:
```python
from ib_async import IB, util
```

Also add `disconnectedEvent` handler in `__init__`:
```python
    def __init__(self) -> None:
        self._order_ib = IB()
        self._config = get_config()
        self._contract_cache: dict[tuple[str, str, str, str], object] = {}
        self._order_ib.disconnectedEvent += self._on_order_disconnected

    def _on_order_disconnected(self) -> None:
        logger.warning("Order IB connection lost — will reconnect on next order")
        self._contract_cache.clear()
```

#### 2F. Remove inline gateway restarts from request paths

**Why**: Current `market_data.py` calls `send_command_to_ibc("RESTART")` when options contracts have no greeks. That is the wrong reliability primitive for Live:

- In the current `gnzsnz/ib-gateway` setup, the IBC command server is disabled, so the call does nothing.
- Even if it worked, missing greeks can be caused by permissions, delayed data, or after-hours behavior, not a dead gateway.
- An unnecessary Live restart is exactly the kind of action that can force a fresh 2FA cycle.

**Recommendation**:

1. Remove automatic gateway restarts from normal request handling.
2. If `ib.isConnected()` is false or the heartbeat fails, let the connection manager reconnect.
3. If market data is missing but the session is healthy, return a structured degraded response that makes the subscription/permission problem explicit.
4. Keep any restart endpoint as an operator action, and prefer it on Paper only.

**Result**: Live stops self-inflicting restarts for conditions that are often data-entitlement issues rather than transport failures.

---

### Phase 3: Monitoring (Observability)

**Goal**: Never let a gateway go down undetected again. Alerts for Paper (4-day silent failure) and Live (2FA timeout).

#### 3A. PrometheusRule for gateway readiness

**Prerequisite**: Prometheus + Alertmanager already running in the cluster (confirmed in k8s-cluster-map memory).

**File**: `k8s/mcp-services/ibkr-prometheus-rules.yaml` (NEW)
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: ibkr-gateway-alerts
  namespace: mcp-services
  labels:
    release: prometheus  # must match your Prometheus Operator's selector
spec:
  groups:
  - name: ibkr-gateway
    rules:
    # Paper gateway not ready for 15 minutes
    - alert: IBKRPaperGatewayDown
      expr: |
        kube_pod_status_ready{namespace="mcp-services",pod=~"ibkr-paper-gateway.*"} == 0
      for: 15m
      labels:
        severity: warning
      annotations:
        summary: "IBKR Paper gateway not ready for 15m"
        description: "Pod {{ $labels.pod }} has been not-ready for 15 minutes. Paper trading is unavailable."

    # Live gateway not ready for 5 minutes (2FA may be needed)
    - alert: IBKRLiveGatewayDown
      expr: |
        kube_pod_status_ready{namespace="mcp-services",pod=~"ibkr-ib-gateway.*"} == 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "IBKR Live gateway not ready — check 2FA"
        description: "Pod {{ $labels.pod }} has been not-ready for 5 minutes. May need 2FA approval on IBKR mobile app."

    # MCP server unhealthy (can't reach gateway)
    - alert: IBKRMCPServerUnhealthy
      expr: |
        kube_pod_status_ready{namespace="mcp-services",pod=~"ibkr-(?:paper-)?[a-f0-9].*"} == 0
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "IBKR MCP server unhealthy"
        description: "Pod {{ $labels.pod }} readiness check failing for 10 minutes."
```

#### 3B. IBKR Trusted IPs (manual step)

**Why**: Your cluster is on-prem (minisforum nodes) with a stable home IP. Adding this IP to IBKR's Trusted IPs list reduces 2FA triggers on the daily AUTO_RESTART.

**Steps** (manual, cannot be automated):
1. Log into IBKR Account Management → Settings → Security → Trusted IPs
2. Add your home public IP (run `curl -s ifconfig.me` from the cluster)
3. This allows the live gateway to re-auth without 2FA when connecting from the same IP

---

### Execution Order

| Step | Phase | Description | Risk | Rollback |
|------|-------|-------------|------|----------|
| 1 | 0A + 1A | Align Helm/chart to the real `gnzsnz` env contract, then pin image digests | Low — config/rendering only | Revert chart templates / revert pinned tags |
| 2 | 1B | Build thin custom gateway image with `xdotool` and wire `IBC_SCRIPTS` dismissal | Medium — new gateway image | Roll back to previous gateway image |
| 3 | 1C | Persist Live state via `TWS_SETTINGS_PATH` PVC | Low — additive | Remove PVC mount and env var |
| 4 | 2A + 2E | Rewrite MCP connection management for long-lived sessions, heartbeat, and reconnect backoff | Medium — core logic | Revert MCP image |
| 5 | 2F | Remove automatic gateway restarts from request handlers | Low | Revert request-path logic |
| 6 | 2C | Split `livez` and `readyz` so readiness reflects actual IB session health | Low | Revert probe endpoints |
| 7 | 1D + 3A | Keep Live alert-not-restart, make Paper auto-restart aggressively, add alerts | Low | Revert probe / alert manifests |
| 8 | 3B | Add IBKR Trusted IPs | Zero — IBKR portal config | Remove IP from portal |

**Steps 1-3**: Gateway/platform hardening. Do these first, and schedule Live changes for a window where you can approve 2FA if IBKR asks for it.

**Steps 4-6**: MCP self-healing changes. Build and deploy as one coordinated MCP release so reconnection logic and readiness semantics land together.

**Steps 7-8**: Operational safety net. These reduce silent failures and unnecessary Live restarts after the core stack is hardened.

---

### What This Does NOT Fix (IBKR Platform Constraints)

1. **Live 2FA on cold restart** — cannot be eliminated for retail accounts. Mitigated by: Trusted IPs, persistent JTS home, no aggressive liveness restarts.
2. **Daily IBKR server reset (~11:45 PM ET)** — unavoidable. AUTO_RESTART at 6 AM handles this.
3. **Weekly session expiry (Saturday)** — must re-authenticate. Paper: automatic. Live: needs 2FA once per week.
4. **No live market data subscription** — `get_price`/`get_tickers` return null for live quotes. Use `get_historical_bars` as workaround, or purchase IBKR market data subscription ($4.50/mo for US equities).
5. **MCP session breaks after pod restart** — requires new Claude Code session. This is a Claude Code / MCP protocol limitation, not fixable server-side.
