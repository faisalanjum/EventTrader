# Monitor — Streaming Price Tracker Design

**Created**: 2026-04-12
**Status**: DESIGN — infrastructure ready, production script not yet built
**Scope**: Continuous per-ticker price streaming inside Claude Code sessions for prediction/earnings workflows

---

## 1. What is the Monitor tool

Monitor is a Claude Code built-in tool that runs a shell command in the background and streams its stdout into the conversation as events. Each stdout line becomes a notification delivered to the session.

### Verified properties

| Property | Value |
|---|---|
| Tool name | `Monitor` |
| Input | `description`, `command`, `timeout_ms`, `persistent` |
| Output | Each stdout line → one conversation notification |
| Max timeout (non-persistent) | 3,600,000 ms (1 hour) |
| Persistent mode | Runs for the lifetime of the session or until `TaskStop` |
| Batching | stdout lines within 200ms grouped into a single notification |
| Parallelism | Multiple monitors can run simultaneously in the same session |
| Stderr | Written to output file (readable via Read), does NOT trigger notifications |
| Auto-stop | Monitors that emit too many events are stopped automatically |

### Two filter patterns

- **Stream filter** — the script watches a live event source (tail -f, inotifywait, WebSocket listener) and prints matching events as they arrive. Event-driven.
- **Poll filter** — the script loops on a timer (sleep N; check; print if changed). Still event-emitting from the Monitor's perspective — notifications only fire when the script prints — but the upstream source is being polled.

### Verified in this session

- BTC price tracker via CoinGecko REST polling — works, delivered ~6 ticks over ~20 minutes with silence between
- Confirmed: notifications arrive independently of user messages
- Confirmed: `TaskStop` terminates the monitor on demand
- Confirmed: persistent monitors continue across user turns

---

## 2. Our requirements

We want a per-ticker streaming price monitor inside each prediction/earnings session that:

1. **Starts at any time** — market open, post-market, overnight, weekend — and does not fail if markets are closed.
2. **Survives market session transitions** — a session started Friday 3 PM should continue through the weekend and deliver ticks Monday pre-market automatically.
3. **Uses IBKR for real data** (our only broker-grade source; crypto/CoinGecko is a fallback for demos).
4. **Pushes ticks event-driven** — not polling-simulated-as-streaming. Our trade daemon already uses `reqMktData(snapshot=False)` which is IBKR's native push-based subscription.
5. **Survives operational events**:
   - Daily 6 AM gateway auto-restart
   - 2FA re-login challenges (we already receive phone alerts for these)
   - Network blips
   - Saturday IBKR contract-definition service outage
6. **Silent when nothing is happening** — no noise during closed markets, just the tick-by-tick when the market is live.

### Out of scope

- Claude Code session itself dying (laptop reboot, terminal closed). Handling this requires an external watchdog (systemd / cron) and is not part of this design.

---

## 3. What is already built and verified

### Layer 1: Kubernetes IBKR gateways

Both paper and live gateway pods are running in namespace `mcp-services` on node `minisforum`.

| Resource | Verified value |
|---|---|
| Paper gateway pod | `ibkr-paper-gateway-*`, running 9+ days |
| Paper gateway service | ClusterIP `10.111.180.120`, port `4004` |
| Live gateway pod | `ibkr-ib-gateway-*`, running 9+ days |
| Live gateway service | ClusterIP `10.111.216.129`, port `4003` |
| Paper TCP 4004 reachable from `minisforum` node | **Yes (verified today)** |
| Live TCP 4003 reachable from `minisforum` node | **Yes (verified today)** |
| Gateway image | `ibkr-gateway-xdotool:stable` (gnzsnz/ib-gateway + xdotool) |
| Manifest | `k8s/mcp-services/ibkr-paper-gateway.yaml` |

**Verified resilience config in the paper gateway manifest** (lines 55-66):

```yaml
TWOFA_TIMEOUT_ACTION: "restart"
RELOGIN_AFTER_TWOFA_TIMEOUT: "yes"
EXISTING_SESSION_DETECTED_ACTION: "secondary"
AUTO_RESTART_TIME: "06:00 AM"
restartPolicy: Always
livenessProbe: tcpSocket port 4002 every 60s
```

### Layer 2: Connection resilience pattern (already in two places)

**In the MCP server** at `ibkr-mcp-server/app/services/client.py`:
- `_on_disconnected` handler wired to `self.ib.disconnectedEvent` (line 29)
- `_reconnect_with_backoff` with delays `[1, 2, 5, 10, 30]` then 60s final retry (lines 44-104)
- `start_heartbeat` + `_heartbeat_loop` running `reqCurrentTimeAsync` every 30s (lines 119-147)
- `util.getLoop.cache_clear()` workaround for ib-async 2.0.1 "Event loop is closed" bug (lines 62-63, 88-89)

**In the trade daemon** at `scripts/trade/ibkr_client.py`:
- `subscribe_quotes` at line 529 — uses `reqMktData(contract, snapshot=False)` for persistent streaming
- Line 564-567: `ticker = self._mktdata_ib.reqMktData(contract, ..., snapshot=False, ...)`
- Line 575: `ticker.updateEvent += lambda t, s=sym: on_update(s, t)` — per-tick callback
- `unsubscribe_quotes` at line 589 — uses `cancelMktData`
- `resubscribe_all` at line 610 — re-establishes subscriptions after reconnect
- Separate heartbeat loop at lines 395-424 covering both mktdata and order connections

### Layer 3: MCP server

| Service | Verified URL | Auth |
|---|---|---|
| Paper MCP | `http://localhost:31101` (NodePort 31101 → 8000) | `Bearer Lgqn5pk8GRb1504c1k0LOEs6hTqjyva` |
| Live MCP | `http://localhost:31100` (NodePort 31100 → 8000) | `Bearer oMSIAFhSdgb7I4LTP4c7r6tAb1lZgPn6` |
| Tokens source | `/home/faisal/EventMarketDB/.mcp.json` |
| Health endpoints | `/health` returns `{"status":"ok"}` for both |
| Gateway status endpoint | `/gateway/status` confirms `connection_status: reachable` |

**Confirmed today**: Live `/ibkr/price?symbol=AAPL` returns `last=260.48` (Friday close) with `bid=null, ask=null` during Saturday market closure.

### Layer 4: Python environment

- `ib_async` version `2.0.1` installed in `./venv`
- Same library used by both the MCP server and the trade daemon

### Prototype streaming script (partial)

`scripts/test_ibkr_stream.py` exists (4,107 bytes). It connects, subscribes via `reqMktData(snapshot=False)`, and prints ticks to stdout. It does NOT yet include the resilience layers (auto-reconnect, resubscribe, heartbeat, Saturday retry). It is adequate for market-hours smoke testing only.

---

## 4. What is NOT yet built

A production-grade streaming script that combines:

1. The `reqMktData(snapshot=False) + ticker.updateEvent` pattern from `scripts/trade/ibkr_client.py:529-620`
2. The `disconnectedEvent` + exponential-backoff reconnect pattern from `ibkr-mcp-server/app/services/client.py:29-104`
3. The 30s heartbeat pattern from the same file (lines 119-147)
4. A subscription registry that replays subscriptions after every reconnect (pattern exists in `resubscribe_all`, line 610)
5. Saturday-aware retry for contract qualification failures
6. stdout-oriented output: price ticks, state changes, heartbeats

None of these patterns are new to the codebase. The work is assembly, not invention.

---

## 5. Proposed system — four layers

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Monitor (Claude Code, persistent: true)            │  built-in
│   • One Monitor per session, runs for session lifetime      │
│   • stdout lines → conversation events                      │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Streaming script (scripts/stream_ibkr.py)          │  TO BUILD
│   • Connects to IBKR gateway via ib_async                   │
│   • reqMktData(snapshot=False) for event-driven ticks       │
│   • Disconnect handler + exponential backoff reconnect      │
│   • Subscription registry replayed after every reconnect    │
│   • 30s heartbeat (reqCurrentTimeAsync)                     │
│   • Saturday-tolerant: retries contract qualification       │
│   • Emits to stdout:                                        │
│       • ticks:     "AAPL $260.48 ▲$0.05 | HH:MM:SS"         │
│       • state:     "[STATE] reconnected, resubscribing N"   │
│       • wait:      "[PAUSE] waiting for gateway, retry ...  │
│       • heartbeat: "[ALIVE] N streams, last tick HH:MM:SS"  │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Connection + subscription resilience               │  existing
│   • Already proven in the MCP server and trade daemon.      │
│   • Layer 3 copies/adapts those patterns — no invention.    │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: K8s IBKR gateway                                   │  running
│   • Running 9+ days, paper + live                           │
│   • Auto-restart, auto-relogin, liveness probe              │
│   • Phone alerts on 2FA challenges (IBKR native)            │
└─────────────────────────────────────────────────────────────┘
```

### Connection choice: direct gateway vs MCP REST

The MCP server's REST endpoint (`/ibkr/price`) is **snapshot-only** — every call qualifies a contract and calls `reqTickersAsync`. Polling it from a bash Monitor would work but would not be true streaming. We already demonstrated this pattern with CoinGecko.

For true event-driven streaming we must bypass the MCP REST layer and connect to the IBKR gateway directly from the script, using the same ClusterIP that the MCP server uses internally (`10.111.180.120:4004` paper, `10.111.216.129:4003` live). This works because the streaming script runs on the `minisforum` node, which has the cluster-internal routing.

Client ID allocation (to avoid collisions):
- MCP server: `clientId=10` (confirmed in `client.py:13`)
- Trade daemon: `clientId=20/21` (confirmed in daemon code)
- Streaming script: `clientId=30` (proposed — unused)

### Behavior across common events

| Event | Behavior (based on verified patterns) |
|---|---|
| Gateway 6 AM restart | TCP connection drops → `disconnectedEvent` fires → exponential-backoff reconnect attempts → resubscribe once connected → streaming resumes |
| 2FA challenge | IBKR pushes phone alert → user approves → gateway resumes → same reconnect path as above |
| Network blip | Same reconnect path |
| IBKR Saturday service outage | Contract qualification fails → script logs "[PAUSE]" and retries every N minutes → resumes when service returns |
| Market close → overnight | Stream goes silent (no ticks to emit). Heartbeat proves script is alive. |
| Market open (pre-market 4 AM ET) | Ticks resume automatically; no action needed |

The only failure mode not recovered by this design is Claude Code session death, which is explicitly out of scope.

---

## 6. Open items

- Write the production streaming script (Layer 3) — adapting existing patterns from `ibkr-mcp-server/app/services/client.py` and `scripts/trade/ibkr_client.py`.
- Confirm the account's market-data subscription level. The live `/ibkr/price` response on Saturday showed `last=260.48, bid=null, ask=null`, which is consistent with snapshot/close-only data. Real-time streaming will only emit useful ticks during market hours if the account has a real-time US equities subscription.
- Decide: one streaming script per ticker (simpler, N processes) vs one script with multi-ticker args (more efficient, one process). Current recommendation: one script, multi-ticker, single gateway connection.
- Decide the exact stdout message format and whether heartbeats should fire every 5/10/15 minutes (defaults TBD).
