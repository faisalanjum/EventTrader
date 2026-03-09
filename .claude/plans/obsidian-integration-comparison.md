# Obsidian Integration: Before vs Now vs CLI Path

## Current State (2026-03-09)

Three layers of Obsidian integration are live. CLI runs as a bare systemd service (no container).

---

## Layer 1: Legacy (still works, not removed)

**Symlink + manual script**

```
earnings skill writes report
  → earnings-analysis/Companies/AAPL/{accession}.md
  → SYMLINK → ~/Obsidian/EventTrader/Earnings/earnings-analysis/Companies/
  → Syncthing → Mac

Thinking extraction:
  → python3 scripts/build-thinking-index.py all   (MANUAL)
  → scans ALL .jsonl transcripts
  → writes ~/Obsidian/.../thinking/runs/{accession}.md
```

| Aspect | Detail |
|--------|--------|
| Scope | Earnings skills only (hardcoded patterns) |
| Trigger | Manual — must run script yourself |
| Vault access | Write-only via symlink |
| Structure | Raw markdown, no frontmatter |
| Files | `scripts/build-thinking-index.py`, `scripts/build-thinking-index.sh` |
| Symlink | `earnings-analysis/Companies` → `~/Obsidian/.../Companies` |

---

## Layer 2: MCP + Hook (live, 2026-03-09)

**Automatic capture + bidirectional vault access + dynamic tagging**

```
ANY agent finishes
  → SubagentStop hook fires automatically
  → infers tags dynamically (ticker, skill type, domain)
  → writes structured .md to ~/Obsidian/.../claude-logs/
  → Syncthing → Mac (real-time)

ANY agent/skill can also:
  → mcp__obsidian__write_note   (create notes with frontmatter)
  → mcp__obsidian__read_note    (read back previous notes)
  → mcp__obsidian__search_notes (BM25 keyword search)
  → mcp__obsidian__update_frontmatter / manage_tags
  → mcp__obsidian__patch_note   (surgical edits)
  → mcp__obsidian__list_directory / get_vault_stats
```

| Aspect | Detail |
|--------|--------|
| Scope | Every agent and skill |
| Trigger | Automatic (SubagentStop hook) |
| Vault access | Read + write + search (14 MCP tools) |
| Structure | YAML frontmatter + dynamic tags |
| Tags | Auto-inferred: ticker (AAPL), skill type (prediction), domain (earnings, guidance, news) |
| Files | `.claude/hooks/obsidian_capture.sh`, `.mcp.json` (obsidian entry) |
| Vault path | `~/Obsidian/EventTrader/Earnings/earnings-analysis/` |
| MCP server | `@mauricio.wolff/mcp-obsidian@latest` (npx, zero deps, Node 18+) |
| Overhead | Zero — process starts/stops with Claude Code session |
| Sync | Syncthing (already running, bidirectional, P2P, free) |

### Known limitations

| Limitation | Detail | Workaround |
|------------|--------|------------|
| No thinking capture | Sub-agent transcripts strip thinking blocks; only parent has them | `Stop` hook on main session runs `build-thinking-index.py` automatically |
| BM25 search only | Keyword matching, no property filters, no tag queries, no graph | Agents use frontmatter + tags for structure; grep-style search is sufficient for CRUD |
| No template expansion | MCP writes raw markdown, no Obsidian template system | Agents format their own markdown (they're better at it anyway) |
| No Dataview queries | Can't run `TABLE ... WHERE ticker = "AAPL"` | Agents use `search_notes` + `read_note` + `get_frontmatter` in sequence |
| No wikilink auto-update | Moving a note doesn't fix [[links]] elsewhere | Agents rarely move notes; create-once pattern |

---

## Layer 3: Obsidian CLI (LIVE, 2026-03-09)

**Obsidian 1.12.4 headless via Xvfb systemd service — 100+ CLI commands**

```
Obsidian runs as systemd user service (obsidian-headless.service)
  → Xvfb :99 provides virtual display
  → obsidian create/search/append/property:set/tags/daily:append
  → Vault: ~/Obsidian/EventTrader/Earnings/earnings-analysis/
  → Syncthing → Mac (real-time)
```

| Aspect | Detail |
|--------|--------|
| Service | `systemctl --user status obsidian-headless` |
| Config | `~/.config/obsidian/obsidian.json` (`"cli": true`) |
| Display | Xvfb :99 (ExecStartPre in service) |
| RAM | ~220 MB (measured) |
| Restart | `Restart=on-failure`, `RestartSec=10` |
| Linger | Enabled (`loginctl enable-linger faisal`) |
| Version | 1.12.4 |
| CLI usage | `DISPLAY=:99 obsidian <command>` from hooks/scripts |

### What CLI adds over MCP

| Feature | MCP | CLI |
|---------|:---:|:---:|
| Create/read/write/delete | Y | Y |
| Search (keyword) | Y | Y |
| Frontmatter/tags | Y | Y |
| Append/prepend | Y | Y |
| Template expansion | N | Y |
| Daily note append | N | Y |
| Wikilink auto-update on move | N | Y |
| Tag rename across entire vault | N | Y |
| Plugin execution (Dataview, Tasks) | N | Y |
| Obsidian search index (property filters, tag queries) | N | Y |
| eval (run JS in vault) | N | Y |
| File history | N | Y |

### Why NOT recommended for this project

**Reliability concerns:**

| Risk | Severity | Detail |
|------|----------|--------|
| Headless Electron crashes | High | Electron under Xvfb is not a supported config. Memory leaks, zombie processes, segfaults are common. No official support from Obsidian team. |
| Vault lock conflicts | High | Obsidian takes an exclusive lock on the vault. If the container's Obsidian AND Mac's Obsidian both open the same vault (via Syncthing), index corruption and `.obsidian/workspace.json` thrashing occur. |
| CLI requires running app | Hard | The CLI is IPC to a running Electron process. If Obsidian crashes, CLI calls fail silently or hang. No retry/health mechanism built in. |
| Xvfb display issues | Medium | Some Obsidian plugin initializations (canvas, graph view) require a real GPU context. Xvfb provides software rendering only. |
| Update brittleness | Medium | Obsidian auto-updates break headless setups. Container must pin version and manually test upgrades. |
| Plugin state drift | Medium | Plugins configured on Mac may not match container. Dataview index, Tasks cache, etc. are per-instance. |
| Container image maintenance | Low-Med | Custom Dockerfile with Obsidian .deb + Xvfb + deps. Not a standard image; must rebuild on every Obsidian release. |

**Efficiency concerns:**

| Metric | MCP | CLI Container |
|--------|-----|---------------|
| RAM | 0 (starts with session) | 300-500 MB (always on) |
| Startup | Instant (npx) | 5-15s (Electron boot) |
| Search latency | ~100ms (file scan) | ~10ms (indexed) but + IPC overhead |
| Failure mode | Tool returns error | Silent hang or crash; needs health check |
| Moving parts | 1 (npx process) | 4 (Xvfb + Electron + IPC socket + vault mount) |

**The 10ms index advantage doesn't matter** when:
- Vault is small (~420 files, 10MB) — BM25 scan is fast enough
- Agents make 1-5 search calls per run, not thousands
- MCP search already returns ranked results with excerpts
- Agents can compensate with `read_note` + `get_frontmatter` for structured filtering

### What WOULD justify the CLI

The CLI becomes worth it only if ALL of these are true:
1. Vault grows to 10,000+ files where BM25 scanning is slow
2. Agents need complex multi-property queries (`tag:#AAPL AND property:confidence > 70`)
3. Template-based note creation is required (vs. agent-formatted markdown)
4. Dataview queries are needed from the server side (vs. Mac GUI)

None of these apply today. If they do in the future, revisit.

---

## Comparison Summary

| | Layer 1 (Legacy) | Layer 2 (MCP+Hook) | Layer 3 (CLI Container) |
|---|---|---|---|
| **Status** | Live (deprecated) | **Live (primary)** | Rejected |
| Captures | Earnings only | Everything | Everything |
| Automatic | No | Yes (SubagentStop hook) | Yes (with hooks) |
| Vault read/search | No | Yes (14 tools) | Yes (100+ commands) |
| Dynamic tags | No | Yes (auto-inferred) | Yes |
| Thinking capture | Manual script | Needs Stop hook (parent transcript) | Same limitation |
| Templates/daily notes | No | No | Yes |
| Plugin execution | No | No | Yes |
| Overhead | Zero | Zero | ~300-500MB RAM |
| Reliability | 100% (filesystem) | 100% (filesystem + MCP) | ~95% (headless Electron) |
| New infra | Symlink | 1 hook + 1 MCP config | Container + Xvfb + image |
| Failure mode | N/A | Tool error (recoverable) | Silent crash (needs watchdog) |

---

## Architecture (final)

```
┌──────────────────────────────────────────────┐
│  Linux Server (headless, no Obsidian app)     │
│                                               │
│  Claude Code                                  │
│    ├─ SubagentStop hook ──→ auto-log with     │
│    │   (obsidian_capture.sh)  dynamic tags    │
│    │                              │            │
│    ├─ MCP: mcp-obsidian ──→ create/search/    │
│    │        (14 tools)       read/tag notes   │
│    │                              │            │
│    └─ Stop hook (planned) ──→ thinking        │
│         (build-thinking-index.py)  extraction │
│                                   │            │
│                    ~/Obsidian/ (vault dir)     │
│                         │                      │
│                    Syncthing (P2P, free)        │
└─────────────────────┬────────────────────────┘
                      │  real-time sync
┌─────────────────────┴────────────────────────┐
│  Mac                                          │
│  Syncthing → ~/Obsidian/ → Obsidian 1.12.4   │
│              (vault dir)   (GUI + CLI local)   │
│                                               │
│  CLI available here for:                      │
│  - Dataview queries                           │
│  - Template management                        │
│  - Tag rename across vault                    │
│  - Graph/backlink exploration                 │
└───────────────────────────────────────────────┘
```

**Key insight:** CLI features (Dataview, templates, graph) are interactive/exploratory. Use them on the Mac where Obsidian runs natively. The Linux server's job is create + search + tag — MCP handles that at 100% reliability.

## Decision: Layer 2 (MCP + Hook) — no container

Reliability and zero-maintenance wins over CLI's power features. The CLI is available on the Mac for any power queries you want to run interactively.
