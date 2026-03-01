# EventTrader: Claude Code on Kubernetes — Technical Feasibility Report

**Date:** February 27, 2026  
**Author:** Claude (compiled from research session with Faisal)  
**Purpose:** Production deployment of Claude Code in containers using Max subscription for automated SEC filing and earnings transcript analysis via the EventTrader pipeline (Redis → Neo4j).

---

## 1. Executive Summary

Claude Code can be run headlessly in Docker containers on Kubernetes using a Max subscription OAuth token instead of API keys. The setup leverages `claude -p` (headless mode) for non-interactive, scriptable analysis of financial documents, with results written directly to Neo4j via MCP. Pre-built container images exist, authentication is solved via `setup-token`, and skills/subagents work in headless mode. The main risks are subscription quota management, concurrent Neo4j write conflicts, and reliance on an undocumented usage-tracking endpoint.

---

## 2. Authentication: Subscription in Containers

### How It Works

- `claude setup-token` generates a long-lived OAuth token (format: `sk-ant-oat01-...`)
- Token is injected via `CLAUDE_CODE_OAUTH_TOKEN` environment variable
- Bypasses the interactive browser OAuth flow entirely

### Known Issues

- **Interactive mode bug (#8938, still open):** Even with the token set, interactive mode still prompts for onboarding. Headless `-p` mode is unaffected — it bypasses this entirely.
- **Token refresh:** `setup-token` produces long-lived tokens (longer than regular credential files which expire ~6 hours), but periodic refresh is still required. A simple cron on a local machine can regenerate and update the K8s secret.

### K8s Secret Setup

```bash
# One-time on local machine
claude setup-token
# Copy the token: sk-ant-oat01-...

# Store in Kubernetes
kubectl create secret generic claude-auth \
  --from-literal=CLAUDE_CODE_OAUTH_TOKEN=<token>
```

---

## 3. Container Images

### Recommended: cabinlab/claude-code-sdk-docker

Pre-built images on GitHub Container Registry with entrypoint scripts that auto-configure auth files when `CLAUDE_CODE_OAUTH_TOKEN` is present. They skip all interactive prompts, mark onboarding complete, and pre-accept trust dialogs.

| Image | Size | Use Case |
|-------|------|----------|
| `ghcr.io/cabinlab/claude-agent-sdk:python` | 693 MB | Full Python SDK support |
| `ghcr.io/cabinlab/claude-agent-sdk:alpine-python` | 474 MB | Lightweight Python |
| `ghcr.io/cabinlab/claude-agent-sdk:typescript` | 607 MB | TypeScript SDK |
| `ghcr.io/cabinlab/claude-agent-sdk:alpine-typescript` | 383 MB | Smallest footprint |

### Alternatives

- **tintinweb/claude-code-container** — 77 stars, security-focused sandbox, read-only input/writable output mounts
- **receipting/claude-code-sdk-container** — Wraps Claude Code as REST API (more complexity than needed for K8s Jobs)

---

## 4. Headless Mode: Performance & Reliability

### Speed: Headless vs Interactive

Headless mode is faster for document analysis tasks. The model itself runs at the same speed, but operational overhead differs significantly:

- **Headless:** Send prompt → process → exit. Average response time is 3–15 seconds depending on complexity. No codebase exploration, no metadata accumulation, no permission prompts.
- **Interactive:** Explores files sequentially, runs validation/safety checks, accumulates metadata in `~/.claude.json` over time (known to cause severe slowdowns on long-running projects).

For EventTrader's use case — "here's a filing, analyze it, return JSON" — headless is the correct mode. There is no codebase to navigate; the task is reasoning about piped-in financial data.

**Container startup overhead:** Each K8s Job needs Node.js + Claude Code initialization = a few seconds of fixed overhead. For high-volume processing, a persistent worker pod avoids this repeated cost.

### Reliability & Auto-Restart

Headless mode returns exit code 0 on success, non-zero on failure — standard Unix behavior compatible with conditional scripts (`&&`, `||`).

**K8s provides the retry layer:**

- Set `backoffLimit` on Jobs (e.g., 2–3 retries) for automatic retry with exponential backoff
- Rate limit failures (429) benefit from the delay between retries
- Auth token expiry causes Job failure after retries → alerts via K8s monitoring

**Recommended error handling pattern in the container:**

```bash
#!/bin/bash
if ! claude -p "$PROMPT" --output-format json > result.json; then
    echo "Claude failed, falling back"
    exit 1  # Let K8s retry
fi
```

Two layers of reliability: script-level error handling inside the container, plus K8s Job-level retry. Far more robust than running interactively on a laptop.

---

## 5. Quota Management: Monitoring & Auto-Stop

### The Problem

Max subscription usage is shared across claude.ai, Claude Code, and Claude Desktop. Running automated K8s Jobs consumes quota that competes with personal interactive use.

### Official Tools

- `/status` command in Claude Code shows remaining allocation (interactive only)
- `Settings > Usage` in claude.ai shows progress bars for 5-hour session and weekly limits
- **No official programmatic API** for checking quota (feature request #21943 is open)

### Undocumented Usage Endpoint (Reverse-Engineered)

A developer discovered the internal API call Claude Code makes:

```
GET https://api.anthropic.com/api/oauth/usage
Authorization: Bearer sk-ant-oat01-...
anthropic-beta: oauth-2025-04-20
```

Returns structured JSON:

```json
{
  "five_hour": { "utilization": 6.0, "resets_at": "2025-11-04T04:59:59Z" },
  "seven_day": { "utilization": 35.0, "resets_at": "2025-11-06T03:59:59Z" },
  "seven_day_opus": { "utilization": 0.0, "resets_at": null }
}
```

### Auto-Stop Architecture

Build a quota-check pre-flight step into the K8s Job controller:

1. Before creating any Claude analysis Job, hit the usage endpoint with the same OAuth token
2. If `seven_day.utilization` > threshold (e.g., 80%), queue the filing for later instead of processing now
3. When the quota resets (weekly cycle), the queue drains automatically
4. This protects personal interactive usage while processing filings opportunistically

**Caveat:** This is an undocumented endpoint that could change without notice.

### Community Monitoring Tools

- **claude-code-limit-tracker** — Real-time quota monitoring per model, separate weekly quotas for Sonnet and Opus. Reports: Max 5x gets 140–280h Sonnet + 15–35h Opus per cycle; Max 20x gets 240–480h Sonnet + 24–40h Opus per cycle.
- **Claude-Code-Usage-Monitor** — Terminal monitoring with ML-based predictions, burn rate analysis, and multi-level alerts.

---

## 6. Skills & Subagents in Containers

### Skills DO Load in Headless Mode

Skill descriptions are loaded into context so Claude knows what's available; full skill content loads when invoked. CLAUDE.md is also automatically loaded from the current directory in headless mode.

### Getting Skills Into the Container

Three approaches, from simplest to most flexible:

**Option A: Global user-scope skills (simplest)**

Skills in `~/.claude/skills/` are available globally across all invocations. One `COPY` line on top of the cabinlab base image:

```dockerfile
FROM ghcr.io/cabinlab/claude-agent-sdk:python
COPY ./my-skills/ /home/node/.claude/skills/
```

**Option B: Plugin system from Git repo (version-controlled)**

Package skills as a Claude Code plugin in a Git repo. Container entrypoint installs them at startup:

```bash
claude plugin marketplace add youruser/eventtrader-skills
claude plugin install filing-analyst@eventtrader-skills
```

Plugins install to `~/.claude/plugins/` and persist for the container's lifetime. Skills are version-controlled, and any container pulls the latest without rebuilding.

**Option C: `--plugin-dir` flag (zero-config)**

Mount a volume with skills and reference at invocation time:

```bash
claude --plugin-dir /mnt/skills/eventtrader -p "Analyze this filing..."
```

No baking into the image, no install step. Just mount and point.

### Subagents Work but Burn Quota Fast

Subagents spawn separate context windows, each consuming tokens independently. Three subagents (scan schema, analyze filing, write results) = 4x the quota burn of a single prompt.

Subagents do not support stepwise plans — they execute immediately with no transparent intermediate output, making debugging difficult until execution finishes.

**Recommendation for EventTrader:** Use a single well-crafted prompt with MCP access for the full scan-analyze-write flow, rather than subagents. Reserve subagents for genuinely complex multi-step workflows where context isolation is essential.

### Subagent MCP Permissions

Subagents must have explicit tool access declared in their YAML frontmatter. Without `mcp__neo4j__*` tools listed, the subagent silently fails to access the database:

```yaml
---
name: filing-analyst
description: Analyzes SEC filings and writes event signals to Neo4j
tools: Read, Bash, mcp__neo4j__execute_query, mcp__neo4j__get_schema
model: opus
---
```

---

## 7. Neo4j Integration via MCP

### Recommended: HTTP Transport for K8s

The Neo4j MCP servers are containerized and support HTTP transport mode designed for scalable, production-ready deployments. Run the MCP server as a separate K8s service:

```yaml
# neo4j-mcp-service deployment (runs independently)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: neo4j-mcp
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: mcp-cypher
        image: python:3.11-slim
        env:
        - name: NEO4J_URI
          value: "neo4j+s://your-instance.databases.neo4j.io"
        - name: NEO4J_USERNAME
          value: "neo4j"
        - name: NEO4J_PASSWORD
          valueFrom:
            secretKeyRef:
              name: neo4j-creds
              key: password
        - name: NEO4J_TRANSPORT
          value: "http"
        - name: NEO4J_MCP_SERVER_PORT
          value: "8080"
        command: ["bash", "-c", "pip install uv && uvx mcp-neo4j-cypher@latest --transport http --server-port 8080 --server-host 0.0.0.0"]
        ports:
        - containerPort: 8080
```

Claude Code Jobs reference it via `--mcp-config`:

```json
{
  "mcpServers": {
    "neo4j": {
      "type": "http",
      "url": "http://neo4j-mcp-service:8080/mcp/"
    }
  }
}
```

### Critical: Write Safety Rules

When multiple K8s Jobs write to the same Neo4j instance concurrently, you risk duplicate nodes and schema drift. Claude generates Cypher dynamically with no guarantee of consistency across invocations.

**Your SKILL.md must enforce these rules:**

```markdown
## Neo4j Write Rules — MANDATORY
- ALWAYS use MERGE with unique identifiers, NEVER raw CREATE for entities
- Company nodes: MERGE (c:Company {ticker: $ticker})
- Filing nodes: MERGE (f:Filing {accession_number: $accession})
- For relationships: MATCH both endpoints first, then MERGE the relationship
- Never create duplicate nodes — check existence via MERGE
- Use ON CREATE SET for initial properties, ON MATCH SET for updates
- All date properties must use ISO 8601 format
```

---

## 8. Kubernetes Deployment Patterns

### Pattern 1: Event-Driven K8s Jobs

Redis pipeline detects new filing → Python controller creates K8s Job:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  generateName: claude-filing-
spec:
  backoffLimit: 2
  ttlSecondsAfterFinished: 3600
  template:
    spec:
      containers:
      - name: claude-analyst
        image: ghcr.io/cabinlab/claude-agent-sdk:python
        command: ["claude", "-p"]
        args:
        - "Analyze this SEC filing for event-driven trading signals. Return JSON with: event_type, sentiment, magnitude, affected_tickers, confidence_score."
        - "--output-format"
        - "json"
        - "--model"
        - "claude-opus-4-6"
        - "--dangerously-skip-permissions"
        - "--mcp-config"
        - "/config/mcp.json"
        envFrom:
        - secretRef:
            name: claude-auth
        volumeMounts:
        - name: mcp-config
          mountPath: /config
      volumes:
      - name: mcp-config
        configMap:
          name: claude-mcp-config
      restartPolicy: Never
```

### Pattern 2: Scheduled CronJobs

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-filing-sweep
spec:
  schedule: "0 6 * * 1-5"  # 6 AM weekdays
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: claude-sweep
            image: ghcr.io/cabinlab/claude-agent-sdk:python
            command: ["claude", "-p"]
            args:
            - "Connect to Neo4j, find unprocessed filings, analyze each for event signals, write results back."
            - "--output-format"
            - "json"
            - "--model"
            - "claude-opus-4-6"
            - "--dangerously-skip-permissions"
            - "--mcp-config"
            - "/config/mcp.json"
            envFrom:
            - secretRef:
                name: claude-auth
```

### Pattern 3: Persistent Worker Pod (Multi-Turn)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: claude-worker
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: claude
        image: ghcr.io/cabinlab/claude-agent-sdk:python
        command: ["sleep", "infinity"]
        envFrom:
        - secretRef:
            name: claude-auth
```

Pipeline `kubectl exec`s into the pod for multi-turn sessions with `--resume` for context continuity.

---

## 9. Model Selection Strategy

| Task | Model | Rationale |
|------|-------|-----------|
| Deep 10-K/10-Q analysis | Opus 4.6 | Complex multi-factor reasoning |
| Earnings call transcripts | Opus 4.6 | Nuance in management tone |
| News sentiment classification | Sonnet | Straightforward, high volume |
| XBRL data structuring | Sonnet | Mechanical parsing |
| Event-graph relationships | Opus 4.6 | Complex causal chains |
| Filing metadata extraction | Sonnet | Simple, repetitive |

Control via `--model` flag per Job. Use Opus strategically for deep analysis, Sonnet for routine work, to manage subscription quota.

---

## 10. Operational Considerations

### Concurrency Limits

- Limit concurrent K8s Jobs to 2–3 maximum
- Batch related documents into single prompts where possible
- Schedule heavy CronJobs for off-hours (early morning/evening)

### Context Window Pressure

The scan-analyze-write flow (read Neo4j schema → scan nodes → read filing → reason → write back) consumes substantial context. For large filings (10-K documents can be 100+ pages), pre-extract relevant sections and pipe only those in rather than asking Claude to read the entire document.

If context fills up mid-analysis, Claude auto-compacts and may lose important details from the schema scan or filing.

### Token Refresh

```bash
# Simple cron on local machine (weekly)
0 0 * * 0 claude setup-token && kubectl create secret generic claude-auth \
  --from-literal=CLAUDE_CODE_OAUTH_TOKEN=$(cat ~/.claude/token) \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## 11. Risk Summary

| Risk | Severity | Mitigation |
|------|----------|------------|
| Quota exhaustion from automated Jobs | High | Pre-flight quota check via usage endpoint; threshold-based gating |
| Duplicate Neo4j nodes from concurrent writes | High | SKILL.md enforces MERGE + unique constraints; never CREATE |
| OAuth token expiry | Medium | Weekly cron refresh + K8s secret update |
| Undocumented usage endpoint changes | Medium | Monitor for breakage; fall back to conservative fixed schedules |
| Subagent quota burn (4x per analysis) | Medium | Prefer single-prompt with MCP over subagent patterns |
| Subagent silent MCP failures | Medium | Declare `mcp__neo4j__*` tools explicitly in agent frontmatter |
| Context overflow on large filings | Medium | Pre-extract relevant sections; limit filing size piped in |
| Skills not loading in container | Low | Use global `~/.claude/skills/`, plugin system, or `--plugin-dir` |
| ToS compliance for automated subscription use | Variable | Anthropic's terms assume "ordinary, individual usage"; production automation should technically use API keys |

---

## 12. Implementation Checklist

1. [ ] Use existing `claude-test` namespace for canary rollout
2. [ ] Generate OAuth token with `claude setup-token` and store as `Secret/claude-auth` in `claude-test`
3. [ ] Create `ConfigMap/claude-mcp-config` with `neo4j-cypher` HTTP endpoint and correct server naming
4. [ ] Create one Claude Job template using `ghcr.io/cabinlab/claude-agent-sdk:python` (no custom image in v1)
5. [ ] Mount repo via `hostPath` to exact path `/home/faisal/EventMarketDB` (required for hooks + scripts)
6. [ ] Set pod env to match `.claude/settings.json` task/team flags and `CLAUDE_PROJECT_DIR`
7. [ ] Run canary test 1: MCP connectivity (`read_neo4j_cypher`)
8. [ ] Run canary test 2: skill invocation (`/neo4j-schema`)
9. [ ] Run canary test 3: agent invocation (`/neo4j-report` or `/news-impact`)
10. [ ] Verify hook execution and expected output artifacts/logs
11. [ ] Only after canary pass, add CronJob or event-driven controller
12. [ ] Add quota guard and concurrency limits as phase-2 hardening
13. [ ] Add OAuth token refresh CronJob

---

## 13. Key Resources

### Container Images
- `ghcr.io/cabinlab/claude-agent-sdk:python` (693 MB)
- `ghcr.io/cabinlab/claude-agent-sdk:alpine-python` (474 MB)

### GitHub Repositories
- [cabinlab/claude-code-sdk-docker](https://github.com/cabinlab/claude-code-sdk-docker) — Pre-built images, auth handling
- [neo4j-contrib/mcp-neo4j](https://github.com/neo4j-contrib/mcp-neo4j) — Neo4j MCP servers (containerized, HTTP transport)
- [TylerGallenbeck/claude-code-limit-tracker](https://github.com/TylerGallenbeck/claude-code-limit-tracker) — Quota monitoring
- [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) — 100+ drop-in subagent definitions

### Documentation
- [Claude Code Headless Mode](https://code.claude.com/docs/en/headless) — Official CLI/headless docs
- [Claude Code Skills](https://code.claude.com/docs/en/skills) — Skill creation and loading
- [Claude Code Plugins](https://code.claude.com/docs/en/discover-plugins) — Plugin marketplace system
- [Neo4j MCP Installation](https://neo4j.com/docs/mcp/current/installation/) — Official Neo4j MCP setup
- [cabinlab Auth Docs](https://github.com/cabinlab/claude-code-sdk-docker/docs/AUTHENTICATION.md) — Container auth details

### Open Issues
- [#8938](https://github.com/anthropics/claude-code/issues/8938) — Interactive mode auth prompt bug (headless unaffected)
- [#21943](https://github.com/anthropics/claude-code/issues/21943) — Feature request for programmatic usage data
- [#16157](https://github.com/anthropics/claude-code/issues/16157) — Max subscription rate limit concerns

---

## 14. Existing Infrastructure Details

This section documents the complete current state of the EventMarketDB Kubernetes cluster that Claude Code containers will be deployed into.

### Cluster Platform

- **Distribution**: K3s (lightweight Kubernetes)
- **kubectl version**: v1.30.12
- **CNI**: Flannel (VXLAN backend)
- **Storage provisioner**: Rancher local-path
- **No docker-compose**: All workloads are native K8s manifests

### Node Topology

| Node | Role | IP | CPU | Allocatable RAM | Taints |
|------|------|------|-----|-----------------|--------|
| **minisforum** | Control Plane | 192.168.40.73 | 16 cores | 57.5 GiB | None (all removed) |
| **minisforum2** | Primary Worker | 192.168.40.72 | 16 cores | 60.5 GiB | None |
| **minisforum3** | Database (Neo4j) | 192.168.40.74 | 16 cores | 123.5 GiB | `database=neo4j:NoSchedule` |

**Total cluster capacity**: 48 CPU cores, ~241.5 GiB RAM

### Namespaces

| Namespace | Purpose |
|-----------|---------|
| `neo4j` | Neo4j 5.26.4 Enterprise graph database |
| `processing` | All worker deployments (event-trader, report-enricher, XBRL workers, edge-writer) |
| `infrastructure` | Redis 7, NATS 2.11.6 (Helm-managed) |
| `monitoring` | Prometheus + Grafana (kube-prometheus-stack via Helm) |
| `keda` | KEDA autoscaler controllers |
| `mcp-services` | MCP Neo4j Cypher + Memory servers (stdio and HTTP modes) |
| `default` | ChromaDB vector store |

### Storage Classes

| Name | Provisioner | Reclaim Policy | Topology | Path |
|------|-------------|---------------|----------|------|
| `local-path` (default) | rancher.io/local-path | Delete | Any node | default |
| `local-path-minisforum3` | rancher.io/local-path | Retain | minisforum3 only | `/opt/local-path` |

### Priority Classes

| Name | Value | Description |
|------|-------|-------------|
| `neo4j-critical` | 1000 | Critical priority for Neo4j database |
| `worker-standard` | 100 | Standard priority for worker pods |

---

### Workloads: Neo4j Database

**Location**: `neo4j` namespace, StatefulSet on minisforum3
**Manifest**: `k8s/neo4j-statefulset.yaml`

| Property | Value |
|----------|-------|
| Image | `neo4j:5.26.4-enterprise` |
| Replicas | 1 |
| CPU | 8 request / 16 limit |
| Memory | 90 GiB request = limit |
| Heap | 24G initial + max |
| Page cache | 56G |
| Global tx memory | 8G |
| Per-tx memory | 4G |
| Tx timeout | 30m |
| JVM | G1GC, 200ms max pause |
| Data PVC | 1536 GiB on `local-path-minisforum3` |
| Logs PVC | 50 GiB on `local-path-minisforum3` |

**Plugins**: APOC, GenAI, GDS — loaded via busybox initContainer that copies JARs from host path `/opt/neo4j/plugins` into an emptyDir volume mounted at `/var/lib/neo4j/plugins`.

**Services**:
- `neo4j` — Headless (ClusterIP: None), ports 7687 + 7474
- `neo4j-bolt` — NodePort 30687 → 7687 (external Bolt access)
- `neo4j-http` — NodePort 30474 → 7474 (external browser access)

**Probes**: Liveness at HTTP :7474 (300s initial delay, 10s period), Readiness (30s initial delay, 3s period).

**Node pinning**: `nodeSelector: kubernetes.io/hostname: minisforum3` + toleration for `database=neo4j:NoSchedule`.

**Config**: Additional ConfigMap `neo4j-config` with `neo4j.conf` contents (memory settings, plugin security, APOC features). Used by the `-fixed` variant of the statefulset.

**Memory increase patch** (`k8s/neo4j-memory-increase-patch.yaml`): Bumps heap to 26G, page cache to 68G, memory to 100 GiB.

---

### Workloads: Processing Namespace

All processing workloads use the `eventtrader-secrets` Secret for environment variables (Neo4j credentials, Redis connection, API keys). All mount logs to host path `/home/faisal/EventMarketDB/logs`.

#### Event Trader

**Manifest**: `k8s/event-trader-deployment.yaml`

| Property | Value |
|----------|-------|
| Image | `faisalanjum/event-trader:latest` |
| Replicas | 1 (fixed, not KEDA-scaled) |
| Command | `python scripts/run_event_trader.py --from-date 2025-01-01 --to-date 2025-07-03 -live` |
| CPU | 500m request / 2 limit |
| Memory | 8 GiB request / 16 GiB limit |
| Node | minisforum2 (nodeSelector) |
| Extra | Blank `.env` file mounted via ConfigMap `empty-env` |

#### Report Enricher

**Manifest**: `k8s/report-enricher-deployment.yaml`

| Property | Value |
|----------|-------|
| Image | `faisalanjum/report-enricher:latest` |
| Replicas | 0 base (KEDA-managed) |
| Command | `python -m redisDB.report_enricher_pod` |
| CPU | 500m request / 2 limit |
| Memory | 2 GiB request / 8 GiB limit |
| Priority | `worker-standard` |
| Affinity | podAntiAffinity to spread across nodes |

**KEDA ScaledObject** (`k8s/report-enricher-scaledobject.yaml`):
- Trigger: Redis list `reports:queues:enrich`
- Target: 5 items per pod
- Min replicas: 1, Max replicas: 5
- Cooldown: 60s

#### XBRL Workers

**Manifest**: `k8s/xbrl-worker-deployments.yaml`

Two active worker tiers (light worker is disabled):

| Worker | CPU Req/Limit | Mem Req/Limit | KEDA Min/Max | Queue | Items/Pod | Cooldown | Grace Period |
|--------|---------------|---------------|-------------|-------|-----------|----------|--------------|
| **Heavy** | 2 / 3 | 6 GiB / 8 GiB | 1 / 2 | `reports:queues:xbrl:heavy` | 2 | 300s | 300s |
| **Medium** | 1.5 / 2 | 3 GiB / 4 GiB | 1 / 3 | `reports:queues:xbrl:medium` | 5 | 180s | 180s |
| ~~Light~~ | ~~1 / 1.5~~ | ~~1.5 GiB / 2 GiB~~ | ~~1 / 4~~ | ~~disabled~~ | — | — | — |

All XBRL workers use node affinity preferring minisforum2/minisforum (weight 100) over minisforum3 (weight 10).

**Single-pod experiment** (`k8s/xbrl-worker-single-pod.yaml`): Heavy worker at 8 CPU / 12 limit, 16 GiB / 24 GiB — used for testing high-resource single-pod performance.

**KEDA ScaledObjects**: `k8s/xbrl-worker-scaledobjects.yaml` — Redis list triggers for each tier.

**Edge patch** (`k8s/xbrl-workers-edge-patch.yaml`): Adds `EDGE_QUEUE=edge_writer:queue` env var to all XBRL worker deployments via `kubectl patch --type merge`.

#### Edge Writer

**Manifest**: `k8s/edge-writer-deployment.yaml`

| Property | Value |
|----------|-------|
| Image | `faisalanjum/xbrl-worker:latest` (same image, different entrypoint) |
| Replicas | 1 (MUST be 1 — single writer pattern) |
| Strategy | `Recreate` (ensures only one instance) |
| Command | `python -m neograph.edge_writer_loop` |
| CPU | 1 request / 2 limit |
| Memory | 1 GiB request / 2 GiB limit |
| Queue | `edge_writer:queue` |
| Node | minisforum2 (nodeSelector) |

---

### Workloads: Infrastructure Namespace

#### Redis

**From DR backup**: `k8s-disaster-recovery/20250708_112320/infrastructure/deployments.yaml`

| Property | Value |
|----------|-------|
| Image | `redis:7` |
| Replicas | 1 |
| Node | minisforum2 (nodeSelector) |
| Storage | PVC `redis-pvc` mounted at `/data` |
| Service | NodePort 31379 → 6379 |
| No resource limits set |

Redis is the backbone of the processing pipeline — all KEDA autoscaling triggers monitor Redis lists.

#### NATS

**Installed via Helm** (chart: nats-1.3.9, app version: 2.11.6)

| Property | Value |
|----------|-------|
| Image | `natsio/nats-box:0.18.0` |
| Service | ClusterIP on port 4222 |
| Headless service | Port 4222 (nats) + 8222 (monitor) |
| Includes | nats-box diagnostic pod |

---

### Workloads: MCP Services Namespace

**Namespace manifest**: `k8s/mcp-services/namespace.yaml`

Three MCP deployments, all on minisforum (control plane node) with tolerations for control-plane taint:

#### mcp-neo4j-cypher (stdio mode — for Claude Desktop)

**Manifest**: `k8s/mcp-services/mcp-neo4j-cypher-deployment.yaml`

| Property | Value |
|----------|-------|
| Image | `mcp/neo4j-cypher:latest` (custom, built from `Dockerfile.cypher`) |
| CPU | 100m request / 250m limit |
| Memory | 256 MiB request / 512 MiB limit |
| Mode | `sleep infinity` — accessed via `kubectl exec` |
| Source | Host-mounted from `/home/faisal/neo4j-mcp-server/servers/mcp-neo4j-cypher` |
| Neo4j URI | `bolt://neo4j-bolt.neo4j:7687` (internal cluster DNS) |

#### mcp-neo4j-memory (stdio mode)

Same pattern as cypher, image `mcp/neo4j-memory:latest`, 512 MiB memory limit. Source from `/home/faisal/neo4j-mcp-server/servers/mcp-neo4j-memory`.

#### mcp-neo4j-cypher-http (HTTP mode — for LangGraph/LangChain)

**Manifest**: `k8s/mcp-services/mcp-neo4j-cypher-http-deployment.yaml`

| Property | Value |
|----------|-------|
| Image | `python:3.11-slim` (installs deps at runtime) |
| CPU | 100m request / 250m limit |
| Memory | 256 MiB request / 512 MiB limit |
| Port | 8000 (HTTP) |
| Service | ClusterIP `mcp-neo4j-cypher-http:8000` |
| Entrypoint | Runs uvicorn serving `mcp.streamable_http_app()` |

**MCP proxy scripts** (`k8s/mcp-services/mcp-proxy-cypher.sh`): Shell scripts that `kubectl exec` into the MCP pod and run the server interactively — used by Claude Desktop for stdio transport.

**Build script** (`k8s/mcp-services/build-mcp-images.sh`): Builds both `mcp/neo4j-cypher:latest` and `mcp/neo4j-memory:latest` Docker images from their respective Dockerfiles using source from the external `neo4j-mcp-server` repo.

---

### Workloads: Default Namespace

#### ChromaDB

**Manifest**: `k8s/chromadb-server.yaml`

| Property | Value |
|----------|-------|
| Image | `chromadb/chroma:0.6.3` |
| Replicas | 1 |
| Node | minisforum2 (nodeSelector) |
| CPU | 2 request / 4 limit |
| Memory | 2 GiB request / 4 GiB limit |
| Storage | hostPath `/home/faisal/EventMarketDB/chroma_db` |
| Service | ClusterIP on port 8000 |
| Probes | Liveness + Readiness at `/api/v1/heartbeat` |

---

### Workloads: Monitoring Namespace

**Installed via Helm** (kube-prometheus-stack):

- **Prometheus** — Metrics collection
- **Grafana** (v12.0.2) — Dashboard UI with sidecar for auto-provisioning dashboards from ConfigMaps

---

### Docker Images & Build Pipeline

4 custom application images pushed to Docker Hub (`faisalanjum/`):

| Image | Dockerfile | Base | Entrypoint |
|-------|-----------|------|------------|
| `faisalanjum/event-trader:latest` | `Dockerfile.event` | python:3.11-slim | `scripts/run_event_trader.py` |
| `faisalanjum/report-enricher:latest` | `Dockerfile.enricher` | python:3.11-slim | `redisDB/report_enricher_pod.py` |
| `faisalanjum/xbrl-worker:latest` | `Dockerfile.xbrl` | python:3.11-slim | `neograph/xbrl_worker_loop.py` |
| (custom neo4j) | `Dockerfile.neo4j` | neo4j:5.26.4-enterprise | Adds APOC plugin |

All Python images install from `requirements.txt` and include system deps (build-essential, gcc, libxml2, git).

### Deployment Scripts

| Script | Purpose |
|--------|---------|
| `scripts/deploy.sh <component>` | Full pipeline: git pull → build → push → rollout |
| `scripts/deploy-all.sh` | Deploys all 3 components (event-trader, xbrl-worker, report-enricher) |
| `scripts/build_push.sh <component>` | Docker build + push to Docker Hub |
| `scripts/rollout.sh <component>` | `kubectl rollout restart` for the deployment; applies KEDA configs for xbrl-worker |
| `scripts/deploy-mcp-http.sh` | kubectl apply + rollout for MCP HTTP service |
| `k8s/mcp-services/build-mcp-images.sh` | Build MCP Docker images from external repo source |

---

### MCP Configuration (Local)

**File**: `.mcp.json` — Configures MCP servers for local Claude Code use:

| Server | Type | Connection |
|--------|------|------------|
| `neo4j-cypher` | stdio | `mcp_servers/local-cypher-server.sh` → `bolt://localhost:30687` (NodePort) |
| `neo4j-memory` | stdio | `mcp_servers/local-memory-server.sh` |
| `perplexity` | stdio | `mcp_servers/local-perplexity-server.sh` |
| `alphavantage` | http | `https://mcp.alphavantage.co/mcp` |

The local cypher server script sets `NEO4J_URI=bolt://localhost:30687` to connect through the NodePort service, activates the project venv, and runs the MCP server entry point from `/home/faisal/neo4j-mcp-server/servers/mcp-neo4j-cypher/src`.

---

### KEDA Autoscaling Summary

All KEDA ScaledObjects use Redis list length triggers. The Redis address is `redis.infrastructure.svc.cluster.local:6379`.

| ScaledObject | Target Deployment | Queue | Items/Pod | Min | Max | Cooldown |
|-------------|-------------------|-------|-----------|-----|-----|----------|
| `report-enricher-scaler` | report-enricher | `reports:queues:enrich` | 5 | 1 | 5 | 60s |
| `xbrl-worker-heavy-scaler` | xbrl-worker-heavy | `reports:queues:xbrl:heavy` | 2 | 1 | 2 | 300s |
| `xbrl-worker-medium-scaler` | xbrl-worker-medium | `reports:queues:xbrl:medium` | 5 | 1 | 3 | 180s |

**Historical safety config** (`k8s/historical-safety-config.yaml`): Reduces max replicas during historical backfill to prevent memory exhaustion.

**Permanent fix** (`k8s/processing/keda-permanent-fix.yaml`): Sets `minReplicaCount: 1` for all workers to ensure instant processing.

---

### Disaster Recovery

**Location**: `k8s-disaster-recovery/20250708_112320/`

Complete YAML exports of all namespace resources taken on 2025-07-08:

| Script | Purpose |
|--------|---------|
| `create-backup.sh` | Exports all resources per namespace + cluster-wide resources (nodes, PVs, storage classes, CRDs, namespaces) |
| `quick-restore.sh` | 7-step automated restore: node labels/taints → namespaces → storage → KEDA/infra/neo4j → wait for critical services → processing/MCP/monitoring → patches |
| `verify-restore.sh` | Post-restore verification |

Backup includes per-namespace directories (processing, infrastructure, neo4j, monitoring, keda, mcp-services) each with deployments, statefulsets, services, configmaps, secrets, PVCs, and scaledobjects.

---

### Architecture Data Flow

```
SEC EDGAR / Benzinga APIs
    ↓
Event Trader (fetches filings + news → Redis queues)
    ↓
Redis Queues (reports:queues:enrich, reports:queues:xbrl:heavy/medium)
    ↓                                    ↓
Report Enricher                    XBRL Workers
(processes reports → Neo4j)        (parse XBRL → Redis edge queue)
                                         ↓
                                   Edge Writer
                                   (single writer → Neo4j relationships)
    ↓
Neo4j Graph Database (1.5TB storage, 90GiB memory)
    ↓
ChromaDB (vector embeddings)
    ↓
MCP Servers → Claude Code / LangGraph access to Neo4j

KEDA → watches Redis queue lengths → auto-scales workers
Prometheus/Grafana → cluster + application monitoring
```

### Resource Budget at Current Scale

**Minimum (all at minReplicas=1)**:
- Event Trader: 500m CPU, 8 GiB
- Report Enricher: 500m CPU, 2 GiB
- XBRL Heavy: 2 CPU, 6 GiB
- XBRL Medium: 1.5 CPU, 3 GiB
- Edge Writer: 1 CPU, 1 GiB
- **Processing total**: 5.5 CPU, 20 GiB

**Maximum (all at maxReplicas)**:
- Event Trader: 500m CPU, 8 GiB (1 pod)
- Report Enricher: 2.5 CPU, 10 GiB (5 pods)
- XBRL Heavy: 4 CPU, 12 GiB (2 pods)
- XBRL Medium: 4.5 CPU, 9 GiB (3 pods)
- Edge Writer: 1 CPU, 1 GiB (1 pod)
- **Processing total**: 12.5 CPU, 40 GiB

**Available headroom for Claude Code Jobs** (on minisforum, currently ~90% idle):
- ~14 CPU cores, ~54 GiB RAM available on control plane node
- minisforum2 has variable headroom depending on XBRL scaling
- minisforum3 is reserved for Neo4j (23.5 GiB remaining after Neo4j)

---

### Live Verification Snapshot (2026-02-28)

This snapshot is from direct `kubectl` inspection on February 28, 2026 and should be treated as the current runtime truth for planning.

### Live Cluster Facts (Verified)

| Item | Live Value |
|------|------------|
| Current context | `kubernetes-admin@kubernetes` |
| Kubernetes version | `v1.30.12` |
| Nodes | `minisforum`, `minisforum2`, `minisforum3` all `Ready` |
| Node taints | Only `minisforum3`: `database=neo4j:NoSchedule` |
| Extra namespace not listed above | `claude-test` (active) |
| CRDs | 17 total (KEDA + monitoring.coreos CRDs present) |
| Resource policies | No `ResourceQuota`, no `LimitRange`, no `NetworkPolicy` |

### Runtime Utilization Signals (Verified)

| Metric | Live Value |
|-------|------------|
| Node memory usage | minisforum: ~41%, minisforum2: ~4%, minisforum3: ~80% |
| Redis queue depth | `reports:queues:enrich=0`, `xbrl:heavy=0`, `xbrl:medium=0`, `xbrl:light=0`, `edge_writer:queue=0` |
| Redis DB size | 3590 keys |
| Neo4j on-disk usage | `/data` ~92G, `/logs` ~176M |
| Neo4j graph size | ~16,425,164 nodes, ~78,623,172 relationships |
| Cluster events | Repeated `DNSConfigForming` warnings across multiple pods |

### Critical Drift Corrections vs Earlier Section 14 Text

| Component | Earlier Text | Live Verified (2026-02-28) |
|----------|--------------|------------------------------|
| Neo4j memory | 90 GiB request/limit, heap 24G, page cache 56G | 100 GiB request/limit, heap 26G, page cache 68G |
| Event Trader deployment | Replica 1 fixed | Replica 0 currently (deployment exists but scaled down) |
| Event Trader args | `--from-date 2025-01-01 --to-date 2025-07-03 -live` | `--from-date 2026-01-28 --to-date 2026-01-31 -live` in live spec |
| XBRL Heavy resources | 2 CPU / 6Gi request, 3 CPU / 8Gi limit | 1500m / 5Gi request, 2500m / 7Gi limit |
| XBRL Medium resources | 1.5 CPU / 3Gi request, 2 CPU / 4Gi limit | 1500m / 5Gi request, 2500m / 7Gi limit |
| XBRL affinity behavior | Generic preferred scheduling | Heavy has required anti-placement from `minisforum`; medium currently only preferred affinity |
| MCP cypher/memory images | `mcp/neo4j-cypher:latest`, `mcp/neo4j-memory:latest` | Running as `python:3.11-slim` with runtime `pip install` entrypoints |
| ChromaDB workload | Documented under default namespace | No active ChromaDB deployment currently observed |
| Control-plane headroom note | "currently ~90% idle" | Not accurate now: minisforum memory is ~41% used |

### Additional Operational Notes for Future Bots

- Large local manifest drift exists: `k8s/` files are not fully synchronized with live objects for Event Trader, XBRL workers, Neo4j memory, and MCP deployment images/entrypoints.
- `k8s/mcp-services/mcp-services.yaml` and related list files include exported live-status style fields and are not clean source-of-truth manifests.
- Processing, mcp-services, and several docs/manifests still include plaintext credential references (for example Neo4j password in some manifests/docs); treat these files as sensitive.
- Live KEDA objects in `processing` are exactly three scalers (`report-enricher`, `xbrl-heavy`, `xbrl-medium`) with `minReplicaCount=1`.
- `DataManagerCentral.initialize_sources()` is currently BENZINGA-only in code (reports/transcripts source managers are commented out), which is a functional behavior detail not reflected in most K8s docs.

---

## 15. Implementation Plan: Minimal Viable Deployment

### Goal

Deploy Claude Code in Kubernetes so the existing `.claude/agents` and `.claude/skills` work unchanged, out of the box.

### Highest-Reliability Minimal Path (What Stands Out)

1. **Run headless only** (`claude -p`) for automation.
2. **Mount the repo read-write at the exact local path**: `/home/faisal/EventMarketDB`. Read-write enables JSONL session transcripts for post-mortem debugging. No write contention — each session gets a unique UUID filename.
3. **Do not repackage agents/skills for v1**. Use the existing project tree directly.
4. **Match MCP server names exactly** to agent tool prefixes (especially `neo4j-cypher`).
5. **Canary first in `claude-test`**; add CronJob/controller only after canary gates pass.

### Why Exact Path Mount Is Non-Negotiable

`.claude/settings.json` uses absolute hook command paths:

- `/home/faisal/EventMarketDB/.claude/hooks/validate_gx_output.sh`
- `/home/faisal/EventMarketDB/.claude/hooks/validate_judge_output.sh`
- `/home/faisal/EventMarketDB/.claude/hooks/block_env_edits.sh`
- `/home/faisal/EventMarketDB/.claude/hooks/guard_neo4j_delete.sh`
- `/home/faisal/EventMarketDB/.claude/hooks/cleanup_after_ok.sh`

If the pod mount path differs, these protections do not run. Also keep `CLAUDE_PROJECT_DIR=/home/faisal/EventMarketDB` because several agents/scripts rely on it.

### v1 Scope: Only 3 K8s Resources

1. `Secret/claude-auth` with `CLAUDE_CODE_OAUTH_TOKEN`
2. `ConfigMap/claude-mcp-config` (MCP endpoints for in-cluster use)
3. One canary `Job` manifest using cabinlab image + hostPath mount

No custom image build, no plugin packaging, no skill copying in v1.

---

### Resource 1: OAuth Secret

```bash
# One-time on local machine
claude setup-token

kubectl create secret generic claude-auth \
  --from-literal=CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-YOUR_TOKEN_HERE \
  -n claude-test
```

### Resource 2: MCP ConfigMap

Keep it minimal for v1. `neo4j-cypher` is the required server name for current agent tool references.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: claude-mcp-config
  namespace: claude-test
data:
  mcp.json: |
    {
      "mcpServers": {
        "neo4j-cypher": {
          "type": "http",
          "url": "http://mcp-neo4j-cypher-http.mcp-services:8000/mcp"
        }
      }
    }
```

Notes:
- Perplexity agents already work through `pit_fetch.py` + API keys from `.env`; no Perplexity MCP required for v1.
- Add `alphavantage` MCP later only if needed by canary workload.

### Resource 3: Canary Job Manifest

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: claude-canary-PLACEHOLDER
  namespace: claude-test
spec:
  backoffLimit: 1
  ttlSecondsAfterFinished: 3600
  template:
    spec:
      nodeSelector:
        kubernetes.io/hostname: minisforum
      restartPolicy: Never
      containers:
      - name: claude
        image: ghcr.io/cabinlab/claude-agent-sdk:python
        workingDir: /home/faisal/EventMarketDB
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          runAsGroup: 1000
          allowPrivilegeEscalation: false
        command: ["/bin/bash", "-lc"]
        args:
        - |
          export PATH="/home/faisal/EventMarketDB/venv/bin:$PATH"
          export PYTHONPATH="/home/faisal/EventMarketDB"
          set -a
          source /home/faisal/EventMarketDB/.env
          set +a

          claude -p "$CLAUDE_PROMPT" \
            --mcp-config /config/mcp.json \
            --strict-mcp-config \
            --dangerously-skip-permissions \
            --output-format json \
            --model claude-opus-4-6
        env:
        - name: CLAUDE_PROJECT_DIR
          value: "/home/faisal/EventMarketDB"
        - name: CLAUDE_CODE_ENABLE_TASKS
          value: "true"
        - name: CLAUDE_CODE_TASK_LIST_ID
          value: "earnings-orchestrator"
        - name: CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS
          value: "1"
        - name: CLAUDE_PROMPT
          value: "REPLACE_ME"
        envFrom:
        - secretRef:
            name: claude-auth
        volumeMounts:
        - name: project
          mountPath: /home/faisal/EventMarketDB
        - name: mcp-config
          mountPath: /config
      volumes:
      - name: project
        hostPath:
          path: /home/faisal/EventMarketDB
          type: Directory
      - name: mcp-config
        configMap:
          name: claude-mcp-config
```

Runtime notes from live toy validation:
- If GHCR pulls are blocked (`403`), use fallback image `node:20-alpine` and install CLI at runtime: `npm install -g @anthropic-ai/claude-code`.
- Keep `workingDir` set to `/home/faisal/EventMarketDB`; this runtime did not support `--project-dir`.
- Keep `--strict-mcp-config` enabled for reliable MCP tool exposure.
- **Mount repo read-write** (no `readOnly: true` on volumeMount). JSONL session transcripts (`.claude/projects/{hash}/{session-uuid}.jsonl`) and sub-agent transcripts land on the host disk automatically — same as local runs. Each session gets a unique UUID filename, so concurrent Jobs writing to the same project directory have zero contention. These transcripts enable post-mortem debugging of agent reasoning, thinking tokens, and tool call sequences. Toy runs used read-only mounts for safety; production mounts should be read-write.

---

### Canary Sequence and Gates

Create three jobs from the manifest above (change `metadata.name` and `CLAUDE_PROMPT` each time):

1. `claude-canary-mcp`
- Prompt: `Use neo4j-cypher MCP to run MATCH (c:Company) RETURN count(c) AS total. Return only the number.`

2. `claude-canary-skill`
- Prompt: `/neo4j-schema`

3. `claude-canary-agent`
- Prompt: `Run /neo4j-report for AAPL filings in January 2026 and return a concise summary.`

Validation commands:

```bash
kubectl wait --for=condition=complete job/claude-canary-mcp -n claude-test --timeout=180s
kubectl logs job/claude-canary-mcp -n claude-test
kubectl logs job/claude-canary-skill -n claude-test
kubectl logs job/claude-canary-agent -n claude-test
```

Pass criteria:
- MCP call succeeds in canary 1.
- Skill resolves and executes in canary 2.
- Agent dispatch works in canary 3.
- No hook path errors in logs.

---

### What You Get Immediately

With this v1 plan, current agents/skills run in K8s with no restructuring:

- Neo4j agents use existing MCP HTTP service.
- Perplexity agents keep using `pit_fetch.py` from the mounted repo.
- Guidance/news/orchestrator workflows keep current task and script behavior.
- Existing `.claude/settings.json` task/team config and hooks remain effective.

### Phase-2 (After Canary Passes)

1. Add event-driven controller (Redis -> Job creation) or CronJob schedules.
2. Add concurrency and quota guards.
3. Add OAuth token refresh automation.
4. Add optional MCP servers (`alphavantage`, `neo4j-memory`) only when needed.

---

## 16. Toy V1 Execution Log (2026-02-28)

This section records the disposable test exactly as executed so any future bot can continue or clean up safely.

### Objective

Run a zero-blast-radius, throwaway Kubernetes test that validates core Claude Code deployment components, then delete everything cleanly.

### Safety Constraints Used

- Dedicated namespace only: `claude-toy-v1`
- No cluster-scoped resources created
- No changes made to existing production namespaces/workloads
- Repo mount configured read-only for the toy job
- Test workload limited to smoke checks only

### Actions Executed

1. Created namespace:
   - `kubectl create namespace claude-toy-v1`
   - Labeled namespace as ephemeral (`purpose=claude-toy-v1`, `lifecycle=ephemeral`, `owner=codex`)
2. Created temporary auth secret:
   - `secret/claude-toy-auth` in `claude-toy-v1`
   - Initial key used was `ANTHROPIC_API_KEY` as a temporary unblock (because no existing `CLAUDE_CODE_OAUTH_TOKEN` secret was present in cluster)
3. Created MCP config:
   - `configmap/claude-toy-mcp-config` with `neo4j-cypher` HTTP endpoint
4. Created smoke job:
   - `job/claude-toy-smoke` using `ghcr.io/cabinlab/claude-agent-sdk:python`
   - Mounted `/home/faisal/EventMarketDB` as read-only

### Runtime Results and Learnings

1. `claude-toy-smoke` failed before startup with `ImagePullBackOff`.
2. Root cause: `ghcr.io/cabinlab/claude-agent-sdk:python` pull denied with `403 Forbidden` from GHCR anonymous token endpoint.
3. Additional image probes:
   - `cabinlab/claude-agent-sdk:python` (Docker Hub): pull denied / not public.
   - `anthropic/claude-code:latest`: pull denied / not public.
4. Viable runtime discovered:
   - Pod `nodeinstall` with `node:20-alpine` successfully ran:
     - `npm install -g @anthropic-ai/claude-code`
     - `claude --version` returned `2.1.63 (Claude Code)`
   - This is a valid fallback for toy tests when GHCR image pulls are blocked.
5. Auth alignment note:
   - Target plan is Claude Code Max auth (`CLAUDE_CODE_OAUTH_TOKEN`).
   - `claude setup-token` was attempted non-interactively and hung during this first run; this was later resolved in the Max-auth rerun below.

### Current Toy Namespace State (at logging time)

- Pods:
  - `imgprobe1` (ImagePullBackOff)
  - `imgprobe2` (ImagePullBackOff)
  - `nodeprobe` (Completed)
  - `nodeinstall` (Completed)
- Jobs:
  - `claude-toy-smoke` (Failed)
- ConfigMaps:
  - `claude-toy-mcp-config`
- Secrets:
  - `claude-toy-auth`

### Exact Cleanup Commands (Safe Rollback to Clean State)

```bash
# Preferred: delete entire disposable namespace
kubectl delete namespace claude-toy-v1 --wait=true --timeout=180s

# Verify cleanup
kubectl get namespace claude-toy-v1
kubectl get all -A | rg claude-toy-v1 || true
kubectl get configmap,secret -A | rg claude-toy-v1 || true
```

### Cleanup Execution Result (2026-02-28)

- `kubectl delete namespace claude-toy-v1 --wait=true --timeout=180s` completed successfully.
- Verification result:
  - `kubectl get namespace claude-toy-v1` -> `NotFound`
  - `kubectl get all -A | rg claude-toy-v1` -> no matches
  - `kubectl get configmap,secret -A | rg claude-toy-v1` -> no matches
- Cluster returned to clean pre-test state.

### Max-Auth Rerun Execution (2026-02-28)

1. Recreated isolated namespace and auth/config resources:
   - `namespace/claude-toy-v1`
   - `secret/claude-toy-auth` with `CLAUDE_CODE_OAUTH_TOKEN` (Max OAuth token source: local Claude credentials)
   - `configmap/claude-toy-mcp-config`
2. Ran `node:20-alpine` based toy jobs with in-container `npm install -g @anthropic-ai/claude-code`.

### Rerun Results

1. **Core test passed in v3** (`job/claude-toy-core-v3` Complete):
   - `claude --version` -> `2.1.63 (Claude Code)`
   - `claude agents` discovered project agents (`58 active agents`)
   - `claude -p` succeeded with Max OAuth and returned expected JSON payload.
2. **Skill invocation test passed** (`job/claude-toy-skill-v1` Complete):
   - Prompt `/neo4j-schema` resolved and executed successfully.
   - Returned full schema summary, confirming skill loading in pod runtime.
3. **Agent/subagent dispatch test passed** (`job/claude-toy-agent-v1` Complete):
   - Prompt `Run /neo4j-report ...` executed and returned AAPL filing results.
   - Confirms project agent loading and subagent/task dispatch path works.
4. **MCP read path validated**:
   - `job/claude-toy-mcp-read-v3` completed but reported tool unavailable with non-strict config path.
   - `job/claude-toy-mcp-debug-v1` completed successfully with strict MCP config and returned `796` for `MATCH (c:Company) RETURN count(c)`.
5. Additional diagnostic (`job/claude-toy-mcp-diag-v4`) confirmed config mount, but `claude ... mcp list` was slow/stalled in non-interactive mode and was deleted to keep the toy run bounded.

### Important Implementation Learnings from Rerun

1. `--project-dir` is not supported by this CLI build (`2.1.63`) in this runtime path; rely on `workingDir` instead.
2. `--dangerously-skip-permissions` is rejected when container runs as root; run as non-root (`uid/gid 1000`) for deterministic headless operation.
3. Max OAuth auth path works in-cluster for inference with `CLAUDE_CODE_OAUTH_TOKEN`.
4. Agent discovery from mounted project works out-of-box (`.claude/agents` detected).
5. MCP read works reliably when using `--strict-mcp-config` with the mounted config file.
6. Skills and agent/subagent workflows are operational in this disposable Kubernetes runtime.

### Requirement Coverage vs Section 15 Plan

| Requirement | Evidence from Toy Run | Status |
|---|---|---|
| Max auth in-cluster | `CLAUDE_CODE_OAUTH_TOKEN` secret + successful `claude -p` | ✅ Proven |
| Existing agents load out-of-box | `claude agents` showed `58 active agents` | ✅ Proven |
| Existing skills load out-of-box | `/neo4j-schema` invocation succeeded | ✅ Proven |
| Agent/subagent execution | `/neo4j-report` invocation succeeded | ✅ Proven |
| MCP Neo4j read | Strict-config run returned `796` company count | ✅ Proven (with `--strict-mcp-config`) |
| Guidance-extractor transcript flow (as-written, 2-phase) | Phase 1 succeeded; Phase 2 failed on `bolt://localhost:30687` | ⚠️ Partially proven |
| Isolated throwaway deployment | All resources confined to `claude-toy-v1` namespace | ✅ Proven |
| Fast/full cleanup with zero residue | Namespace deletion + residue checks completed | ✅ Proven |

### Current State Before Final Cleanup (second run)

- Jobs present in toy namespace:
  - failed exploratory jobs: `claude-toy-core`, `claude-toy-core-v2`, `claude-toy-mcp-read`, `claude-toy-mcp-read-v2`
  - successful validation jobs: `claude-toy-core-v3`, `claude-toy-skill-v1`, `claude-toy-agent-v1`, `claude-toy-mcp-read-v3`, `claude-toy-mcp-debug-v1`
- ConfigMap: `claude-toy-mcp-config`
- Secret: `claude-toy-auth`

### Final Cleanup Commands (second run)

```bash
kubectl delete namespace claude-toy-v1 --wait=true --timeout=180s
kubectl get namespace claude-toy-v1
kubectl get all -A | rg claude-toy-v1 || true
kubectl get configmap,secret -A | rg claude-toy-v1 || true
```

### Final Cleanup Execution Result (second run, 2026-02-28)

- `kubectl delete namespace claude-toy-v1 --wait=true --timeout=180s` completed successfully.
- Verification result:
  - `kubectl get namespace claude-toy-v1` -> `NotFound`
  - `kubectl get all -A | rg claude-toy-v1` -> no matches
  - `kubectl get configmap,secret -A | rg claude-toy-v1` -> no matches
- Cluster returned to clean pre-test state after second run.

### Guidance-Extractor Write-Path Test (third run, 2026-02-28)

Objective: verify the highest-value real use case (`/guidance-extractor` on transcript) with subagents + references + file writes, while keeping cluster/runtime 100% disposable.

Safety controls used:
- Dedicated namespace: `claude-toy-write-v1`
- Repo mounted read-only in pod (`/home/faisal/EventMarketDB`)
- Prompt explicitly limited file writes to `/tmp/guidance-toy/result.txt`
- Post-run probe attempted repo write and confirmed read-only enforcement

Invocation tested:
- `/guidance-extractor SMPL transcript SMPL_2023-01-05T08.30.00-05.00 MODE=dry_run`

#### Run v2 (node:20-alpine, no SHELL env)

- Result: completed with orchestrator summary, but both phases blocked.
- Reported blocker: Bash tool unavailable due missing `SHELL` environment variable.
- Status file written: `/tmp/guidance-toy/result.txt`
- No JSON extraction payloads created.

#### Run v3 (node:20 + `SHELL=/bin/bash`)

- Result: completed; shell blocker resolved.
- Phase 1 (`guidance-extract`) status: **success**
  - 11 guidance items extracted (dry-run)
  - IDs validated, no ID errors reported
  - JSON payload file created: `/tmp/gu_SMPL_SMPL_2023-01-05T08.30.00-05.00.json`
- Phase 2 (`guidance-qa-enrich`) status: **failed**
  - Error path: Neo4j connection refused at `bolt://localhost:30687`
  - No Q&A enrichment write batch completed
- Status file written: `/tmp/guidance-toy/result.txt`
- Repo write probe: `Read-only file system` (expected, confirms no repo mutation)

#### What this proves

1. Skill invocation works in K8s (`/guidance-extractor` executed).
2. Subagent orchestration works (Phase 1 and Phase 2 agents both invoked by skill flow).
3. Reference-heavy path works at least through full Phase 1 extraction pipeline.
4. Write tool/file output works (`/tmp` artifacts and status file created).
5. Safety guard works (repo write attempts blocked by read-only mount).

#### Roadblocks (important)

1. `SHELL` must be set in container runtime for this agent stack (`SHELL=/bin/bash` recommended).
2. `guidance-qa-enrich` path is not fully K8s-portable as-is in this runtime because it depends on direct Bolt connectivity to `localhost:30687` (not valid inside pod).
3. Therefore, "`guidance-extractor` transcript two-phase flow works exactly as written end-to-end in K8s" is **not yet true**; it is **partially true** (Phase 1 yes, Phase 2 blocked by Neo4j endpoint assumption).

#### Recommended fix before production

1. Make Neo4j endpoint configurable for both phases via env, defaulting to in-cluster service (not localhost).
2. Ensure Phase 2 honors `MODE=dry_run` without requiring live Bolt write path.
3. Keep `SHELL=/bin/bash` in the Job template.

#### Third-Run Cleanup Execution Result (2026-02-28)

- `kubectl delete namespace claude-toy-write-v1 --wait=true --timeout=180s` completed successfully.
- Verification result:
  - `kubectl get ns claude-toy-write-v1` -> `NotFound`
  - `kubectl get all -A | rg claude-toy-write-v1` -> no matches
  - `kubectl get cm,secret -A | rg claude-toy-write-v1` -> no matches
- Cluster returned to clean pre-test state after third run.
