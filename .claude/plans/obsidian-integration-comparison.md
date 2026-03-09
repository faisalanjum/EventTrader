# Obsidian Integration: Architecture & Setup Guide

## Current State (2026-03-09)

Three layers of Obsidian integration are live. All work together.

---

## Architecture

```
┌───────────────────────────────────────────────────┐
│  Linux Server (headless)                           │
│                                                    │
│  Obsidian 1.12.4 (Xvfb headless, systemd service) │
│    └─ CLI: DISPLAY=:99 obsidian <command>          │
│       100+ commands: create, search, tags,         │
│       property:set, daily:append, eval, etc.       │
│                                                    │
│  Claude Code                                       │
│    ├─ MCP: mcp-obsidian (14 tools, agent writes)   │
│    ├─ CLI: via Bash tool or hooks                  │
│    └─ SubagentStop hook (auto-capture + tags)      │
│                                                    │
│                ~/Obsidian/ (vault directory)        │
│                      │                             │
│                 Syncthing (P2P, free, real-time)    │
└──────────────────────┬────────────────────────────┘
                       │
┌──────────────────────┴────────────────────────────┐
│  Mac                                               │
│  Syncthing → ~/Obsidian/ → Obsidian 1.12.4 GUI    │
│                             (full app + CLI local)  │
└───────────────────────────────────────────────────┘
```

---

## Layer 1: Legacy (still works, not removed)

**Symlink + manual script**

| Aspect | Detail |
|--------|--------|
| Scope | Earnings skills only (hardcoded patterns) |
| Trigger | Manual — `python3 scripts/build-thinking-index.py all` |
| Vault access | Write-only via symlink |
| Structure | Raw markdown, no frontmatter |
| Files | `scripts/build-thinking-index.py`, `scripts/build-thinking-index.sh` |
| Symlink | `earnings-analysis/Companies` → `~/Obsidian/.../Companies` |

---

## Layer 2: MCP + Hook (live)

**Automatic capture + bidirectional vault access + dynamic tagging**

| Aspect | Detail |
|--------|--------|
| Scope | Every agent and skill |
| Trigger | Automatic (SubagentStop hook) |
| Vault access | Read + write + search (14 MCP tools) |
| Structure | YAML frontmatter + dynamic tags |
| Tags | Auto-inferred: ticker (AAPL), skill type (prediction), domain (earnings) |
| Files | `.claude/hooks/obsidian_capture.sh`, `.mcp.json` (obsidian entry) |
| MCP server | `@mauricio.wolff/mcp-obsidian@latest` (npx, zero deps, Node 18+) |
| Overhead | Zero — process starts/stops with Claude Code session |
| Best for | Agent writes, auto-capture, basic search |

### MCP Tools (14)

`write_note`, `read_note`, `patch_note`, `delete_note`, `move_note`, `move_file`,
`list_directory`, `read_multiple_notes`, `search_notes` (BM25), `get_frontmatter`,
`update_frontmatter`, `get_notes_info`, `get_vault_stats`, `manage_tags`

---

## Layer 3: Obsidian CLI (live)

**Obsidian 1.12.4 headless via Xvfb systemd service — 100+ commands**

| Aspect | Detail |
|--------|--------|
| Service | `systemctl --user status obsidian-headless` |
| Config | `~/.config/obsidian/obsidian.json` (`"cli": true`) |
| Display | Xvfb :99 (virtual framebuffer, started by service) |
| RAM | ~220 MB (measured) |
| Restart | `Restart=on-failure`, `RestartSec=10` (auto-heals) |
| Linger | `loginctl enable-linger faisal` (survives logout + reboot) |
| Version | 1.12.4 |
| Usage | `DISPLAY=:99 obsidian <command>` |
| Best for | Indexed search, property queries, tags, daily notes, templates, Dataview |

### What CLI adds over MCP

| Feature | MCP | CLI |
|---------|:---:|:---:|
| Create/read/write/delete | Y | Y |
| Search (keyword) | Y | Y |
| Frontmatter/tags CRUD | Y | Y |
| Append/prepend | Y | Y |
| **Indexed search** (instant, pre-built) | N | Y |
| **Property-aware queries** | N | Y |
| **Template expansion** | N | Y |
| **Daily note append** | N | Y |
| **Wikilink auto-update on move** | N | Y |
| **Tag rename across vault** | N | Y |
| **Plugin execution** (Dataview, Tasks) | N | Y |
| **eval (run JS in vault)** | N | Y |
| **File history** | N | Y |
| **Backlinks/orphans/deadends** | N | Y |
| **TUI mode** | N | Y |

### When to use which

| Use case | Use |
|----------|-----|
| Agent creates a note during a run | MCP (`write_note`) |
| Auto-capture agent output | Hook → MCP |
| Search for notes by content | CLI (`search query="..."`) |
| Filter by tag or property | CLI (`tag name="#AAPL"`) |
| Append to daily note | CLI (`daily:append content="..."`) |
| Set/read YAML properties | CLI (`property:set`, `property:read`) |
| Create from template | CLI (`create template="..."`) |
| Bulk tag operations | CLI (`tags`, `tag`) |
| Agent reads a known file | Either (both work) |

---

## How to Use the CLI

### Prerequisites (already done on this server)

1. Install Obsidian 1.12.4: `sudo dpkg -i obsidian_1.12.4_amd64.deb`
2. Install Xvfb: `sudo apt install xvfb` (provides virtual display)
3. Set config key — edit `~/.config/obsidian/obsidian.json`:
   ```json
   {
     "cli": true,
     "updateDisabled": true,
     "vaults": {
       "earnings-analysis": {
         "path": "/home/faisal/Obsidian/EventTrader/Earnings/earnings-analysis",
         "open": true
       }
     }
   }
   ```
   **IMPORTANT:** The key is `"cli": true`, NOT `"enableCli": true`. Found by reading the asar source — undocumented.

4. Start Xvfb + Obsidian:
   ```bash
   Xvfb :99 -screen 0 1024x768x24 &
   DISPLAY=:99 obsidian --no-sandbox &
   sleep 10  # wait for Electron to boot
   ```

5. Verify: `DISPLAY=:99 obsidian version` → `1.12.4 (installer 1.12.4)`

### Systemd Service (already running)

File: `~/.config/systemd/user/obsidian-headless.service`

```ini
[Unit]
Description=Obsidian Headless (Xvfb + CLI)
After=network.target

[Service]
Type=simple
Environment=DISPLAY=:99
ExecStartPre=/bin/bash -c 'pgrep -f "Xvfb :99" || Xvfb :99 -screen 0 1024x768x24 &'
ExecStartPre=/bin/sleep 1
ExecStart=/opt/Obsidian/obsidian --no-sandbox
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

Commands:
```bash
systemctl --user start obsidian-headless
systemctl --user stop obsidian-headless
systemctl --user restart obsidian-headless
systemctl --user status obsidian-headless
journalctl --user -u obsidian-headless -f   # logs
```

### CLI Command Reference (commonly used)

All commands require `DISPLAY=:99` prefix on headless Linux.

```bash
# === NOTES ===
obsidian create path="folder/note" content="# Title\n\nBody"
obsidian create path="folder/note" template="my-template" overwrite
obsidian read file="note-name"                    # resolve by wikilink name
obsidian read path="folder/note.md"               # resolve by exact path
obsidian append file="note" content="new line"
obsidian prepend file="note" content="top line"
obsidian delete file="note"
obsidian move file="note" to="new-folder/"
obsidian rename file="note" name="new-name"

# === SEARCH ===
obsidian search query="earnings AAPL" limit=10
obsidian search query="earnings" path="Companies/" format=json
obsidian search:context query="guidance" limit=5   # shows matching lines

# === PROPERTIES (YAML frontmatter) ===
obsidian property:set file="note" name="ticker" value="AAPL"
obsidian property:set file="note" name="tags" value="a, b, c" type=list
obsidian property:read file="note" name="ticker"
obsidian property:remove file="note" name="old-key"
obsidian properties file="note" format=yaml        # show all properties

# === TAGS ===
obsidian tags                                       # list all tags
obsidian tags counts sort=count                     # with counts
obsidian tag name="#AAPL"                           # tag info + files
obsidian tag name="#AAPL" verbose                   # list files with tag

# === DAILY NOTES ===
obsidian daily                                      # open/create today's note
obsidian daily:read                                 # read today's note
obsidian daily:append content="Log entry at $(date)"
obsidian daily:prepend content="Priority item"
obsidian daily:path                                 # get path

# === VAULT INFO ===
obsidian vault                                      # name, path, file count, size
obsidian files folder="Companies/" ext=md           # list files
obsidian folders                                    # list folders
obsidian backlinks file="note"                      # what links to this note
obsidian links file="note"                          # outgoing links
obsidian orphans                                    # files with no incoming links
obsidian deadends                                   # files with no outgoing links
obsidian unresolved                                 # broken [[links]]

# === PLUGINS ===
obsidian plugins:enabled                            # list enabled plugins
obsidian plugin:enable id="dataview"
obsidian plugin:disable id="dataview"

# === TEMPLATES ===
obsidian templates                                  # list available templates
obsidian template:read name="my-template" resolve   # read with variables resolved
obsidian create path="new-note" template="my-template"

# === ADVANCED ===
obsidian eval code="app.vault.getMarkdownFiles().length"   # run JS
obsidian command id="editor:toggle-bold"                    # execute command
obsidian commands filter="editor"                           # list commands
obsidian reload                                             # reload vault index
```

### Using CLI from Claude Code hooks

In hook scripts, always set DISPLAY:
```bash
#!/usr/bin/env bash
export DISPLAY=:99
obsidian create path="logs/$(date +%Y-%m-%d)" content="$1"
obsidian property:set file="$(date +%Y-%m-%d)" name="source" value="hook"
```

### Using CLI from Claude Code agents (via Bash tool)

Agents can call CLI commands via the Bash tool:
```bash
DISPLAY=:99 obsidian search query="AAPL prediction confidence" limit=5
DISPLAY=:99 obsidian property:read file="attribution-report" name="primary_driver"
```

### Troubleshooting

| Problem | Fix |
|---------|-----|
| `Missing X server or $DISPLAY` | Xvfb not running. Check: `pgrep -f "Xvfb :99"` |
| `CLI is not enabled` | Wrong config key. Must be `"cli": true` in `~/.config/obsidian/obsidian.json` |
| `Vault not found` | Check obsidian.json has correct vault path with `"open": true` |
| `File not found` (with `file=`) | `file=` resolves by wikilink name (no path). Use `path=` for exact paths |
| Segfault on startup | Missing `--no-sandbox` flag |
| Search returns empty | Run `obsidian reload` to rebuild index |
| Memory leak (>500MB) | `systemctl --user restart obsidian-headless` |
| Service won't start after reboot | Check: `loginctl enable-linger faisal` |
| GPU errors in logs | Normal — Xvfb is software rendering. Harmless. Ignore. |

---

## Comparison Summary

| | Layer 1 (Legacy) | Layer 2 (MCP+Hook) | Layer 3 (CLI) |
|---|---|---|---|
| **Status** | Live (deprecated) | **Live** | **Live** |
| Captures | Earnings only | Everything (auto) | Everything (manual/scripted) |
| Vault read/search | No | Yes (14 tools, BM25) | Yes (100+ cmds, indexed) |
| Dynamic tags | No | Yes (auto-inferred) | Yes (property:set, tags) |
| Templates | No | No | Yes |
| Daily notes | No | No | Yes |
| Plugin execution | No | No | Yes |
| Overhead | Zero | Zero | ~220 MB RAM |
| Reliability | 100% | 100% | 99%+ (systemd auto-restart) |

## Decision: All three layers live — MCP for agent writes, CLI for power queries
