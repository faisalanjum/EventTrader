# Guidance Thinking Harvester — Setup Runbook

External post-hoc harvester that captures guidance-extraction thinking into
the Obsidian vault **without touching the K8s extraction pipeline**. Runs on
the minisforum host.

## What it does

Watches `/home/faisal/.claude/projects/-home-faisal-EventMarketDB/*.jsonl`
(top-level only) for completed `/extract ... TYPE=guidance` sessions. When
one completes, it derives the quarter and writes
`earnings-analysis/Companies/{TICKER}/events/{Q}/guidance/thinking_{asset}.md`
+ `subagents_{asset}/`.

**Zero coupling to:** `scripts/extraction_worker.py`,
`scripts/trigger-extract.py`, `scripts/guidance_trigger_daemon.py`,
`k8s/processing/*.yaml`, or `.claude/settings.json`.

## Modes

```bash
# Manual single-session harvest
venv/bin/python scripts/harvest_guidance_sessions.py one <SESSION_ID>

# One-shot reconciliation (recommended via cron every 2 hours)
venv/bin/python scripts/harvest_guidance_sessions.py scan --since-hours 2

# Long-running event-driven watcher (requires watchdog package)
venv/bin/python scripts/harvest_guidance_sessions.py watch \
    --debounce-seconds 15
```

The `scan` and `one` modes have **zero Python package dependencies** beyond
what's already in the repo's venv. The `watch` mode requires the `watchdog`
package; it exits cleanly with install instructions if missing.

## Install steps (minisforum host only)

### Option 1 — Cron reconciliation (simplest, no extra packages)

Add to `/etc/cron.d/harvest-guidance`:

```cron
# Reconcile guidance thinking harvest every 2 hours
0 */2 * * * faisal cd /home/faisal/EventMarketDB && \
    venv/bin/python scripts/harvest_guidance_sessions.py scan \
    --since-hours 3 \
    >> /home/faisal/EventMarketDB/logs/harvest-guidance.log 2>&1
```

Verify:
```bash
sudo crontab -u faisal -l | grep harvest-guidance
tail -f /home/faisal/EventMarketDB/logs/harvest-guidance.log
```

**Latency:** 0–2 h. Acceptable for audit artifacts.

### Option 2 — Event-driven watcher + reconciliation backup (recommended)

1. Install `watchdog` in the project venv (one-time):
   ```bash
   /home/faisal/EventMarketDB/venv/bin/pip install watchdog
   ```

2. Create systemd service `/etc/systemd/system/harvest-guidance.service`:
   ```ini
   [Unit]
   Description=Obsidian guidance thinking harvester (event-driven)
   After=network-online.target

   [Service]
   Type=simple
   User=faisal
   Group=faisal
   WorkingDirectory=/home/faisal/EventMarketDB
   ExecStart=/home/faisal/EventMarketDB/venv/bin/python \
       /home/faisal/EventMarketDB/scripts/harvest_guidance_sessions.py watch \
       --debounce-seconds 15
   Restart=on-failure
   RestartSec=10
   StandardOutput=append:/home/faisal/EventMarketDB/logs/harvest-guidance-watch.log
   StandardError=append:/home/faisal/EventMarketDB/logs/harvest-guidance-watch.log

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable + start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now harvest-guidance.service
   sudo systemctl status harvest-guidance.service
   ```

4. Add the cron reconciliation from Option 1 as a backup (for daemon restart
   gaps / missed inotify events):
   ```cron
   0 */2 * * * faisal cd /home/faisal/EventMarketDB && \
       venv/bin/python scripts/harvest_guidance_sessions.py scan \
       --since-hours 3 \
       >> /home/faisal/EventMarketDB/logs/harvest-guidance.log 2>&1
   ```

**Latency:** ~instant (debounce 15 s after last write).
**Idle cost:** ~20 MB RAM, 0 % CPU (sleeps on kernel inotify events).

### Disable / rollback

```bash
sudo systemctl disable --now harvest-guidance.service
sudo rm /etc/cron.d/harvest-guidance
# That's it — no pipeline code is touched.
```

## Verification

After install, trigger a guidance extraction (or wait for the next K8s worker
run) and verify:

```bash
# List recent guidance harvests
ls earnings-analysis/Companies/*/events/*/guidance/thinking_*.md

# Spot-check frontmatter of a fresh harvest
head -20 earnings-analysis/Companies/BURL/events/Q4_FY2025/guidance/thinking_8k.md

# Watch the log
tail -f logs/harvest-guidance-watch.log    # if systemd service
tail -f logs/harvest-guidance.log          # if cron only
```

Expected frontmatter fields:
```yaml
component: guidance
source_asset: 8k            # or 10q / 10k / transcript
source_id: <accession>      # or transcript id
ticker: <TICKER>
quarter: <Q>_FY<YYYY>
sdk_session_id: <uuid>
session_pattern: EMBED-visible | EMBED-redacted | FORK
```

## Troubleshooting

**Nothing harvested after a live extraction:**
- Check `tail -f logs/harvest-guidance-watch.log` for skip reasons
- Common skip causes:
  - `session not complete` → session still in progress (wait for end_turn marker)
  - `not a /extract guidance session` → correctly filtered out
  - `quarter not derivable` → Neo4j query returned no rows (ticker/fiscal data missing)
  - `already harvested` → idempotency working as designed (re-run is no-op)

**Daemon keeps restarting:**
- `journalctl -u harvest-guidance.service -n 100`
- Most likely: `watchdog` not installed → install it (Option 2 step 1)
- Or: `ImportError` on `neograph.Neo4jConnection` → check `.env` loading

**Missed events:**
- Cron reconciliation catches anything missed within the last 3 hours
- Manual backfill: `python scripts/harvest_guidance_sessions.py scan --since-hours 24`

## Pipeline-pipeline isolation guarantee

| File | Touched by this tool? |
|---|---|
| `scripts/extraction_worker.py` | **NO** |
| `scripts/trigger-extract.py` | **NO** |
| `scripts/guidance_trigger_daemon.py` | **NO** |
| `k8s/processing/extraction-worker.yaml` | **NO** |
| `k8s/processing/guidance-trigger.yaml` | **NO** |
| `.claude/settings.json` | **NO** |
| `.claude/hooks/obsidian_capture.py` | **NO** |

**All changes are additive and live in new files only.** Disabling the
harvester (systemctl disable + remove cron) leaves the guidance extraction
pipeline in its exact current state.
