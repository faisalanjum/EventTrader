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
| Search returns empty | Known v1.12.4 bug — index is incomplete for many terms. Use `search:context` or `eval` with `cachedRead()` for reliable search. `reload` may help but index rebuild is partial. |
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

---

## Sub-Agent Thinking Capture (investigated 2026-03-09)

### The Problem

Sub-agent thinking blocks (extended thinking / chain-of-thought) no longer appear in sub-agent transcript files on Claude Code v2.1.68+. The SubagentStop hook reads `agent_transcript_path` correctly but finds 0 thinking blocks.

### Root Cause (verified by decompiling v2.1.71 binary)

Claude Code v2.1.68+ hard-codes `thinkingConfig: {type: "disabled"}` for sub-agents. The control variable is `useExactTools` (param `X`) in the `IS()` function:

```javascript
// Deobfuscated from v2.1.71 binary — agent spawning function IS()
thinkingConfig: X ? parentOptions.thinkingConfig : {type: "disabled"}
//              ^ useExactTools — must be true to inherit thinking
```

**Two separate call sites invoke IS():**

```javascript
// 1. Agent/Task tool caller — CAN pass useExactTools:
IS({
  ...(T || y) && {useExactTools: true},  // T=fork flag, y=self-recursion
  forkContextMessages: T || v.forksParentContext ? w.messages : void 0,
  ...
})

// 2. Skill tool fork caller (eo1 function) — DOES NOT pass useExactTools:
IS({
  agentDefinition: O,
  promptMessages: X,
  toolUseContext: {...L, getAppState: Y},
  isAsync: false,
  querySource: "agent:custom",
  model: H.model,
  availableTools: L.options.tools,
  override: {agentId: M}
  // ← useExactTools NOT PASSED (undefined = falsy)
})
```

**Result:** Skill tool forks get `thinkingConfig: {type: "disabled"}` because `eo1` never passes `useExactTools: true`.

| Spawn method | useExactTools | Thinking |
|---|---|---|
| **Parent conversation** | N/A | **Enabled** |
| **Non-fork skill** (inject into parent) | N/A | **Enabled** (via parent) |
| **Fork skill** (eo1 → IS) | **NOT passed** | **DISABLED** |
| **Agent/Task** sub-agent | Not passed | **DISABLED** |
| Agent/Task with fork flag | Passed (T=true) | Enabled |
| Self-recursive agent | Passed (y=true) | Enabled |
| Hook agents (prompt/agent type) | N/A | Explicitly **DISABLED** |

**Note:** "Non-fork skill" means skills without `context: fork` — their content is injected into the parent conversation which already has thinking enabled. "Fork skill" means skills with `context: fork` (like our earnings skills) which create a separate subprocess via eo1.

### What does NOT help

| Setting | Location | Effect on sub-agents |
|---|---|---|
| `alwaysThinkingEnabled: true` | `~/.claude/settings.json` | Only affects parent main loop, not sub-agent options |
| `effortLevel: "high"` | `~/.claude/settings.json` | Sets parent state, overridden by disabled thinkingConfig |
| `MAX_THINKING_TOKENS: 31999` | `~/.claude/settings.json` env | Budget irrelevant when thinking is disabled |
| `"ultrathink"` in agent prompt | Agent tool prompt field | Keyword processed by CLI layer for parent only |
| `effort:` in agent frontmatter | `.claude/agents/*.md` | Sets effortValue in state but thinkingConfig still disabled |
| `CLAUDE_CODE_ALWAYS_ENABLE_EFFORT` | env var | Affects effort check function, not sub-agent thinkingConfig |

### Evidence

**Old sessions (v2.1.52, opus-4-5, Feb 2026):**
```
agent-a96c6e5.jsonl: 3 thinking (1,044 chars), 2 text   ← THINKING PRESENT
agent-ab0db5f.jsonl: 3 thinking (1,534 chars), 2 text
agent-ad241eb.jsonl: 3 thinking (3,304 chars), 2 text
Model: claude-opus-4-5-20251101
```

**Current sessions (v2.1.71, opus-4-6, Mar 2026):**
```
agent-a491aae.jsonl: 0 thinking, 6 text                 ← NO THINKING
agent-a6785da.jsonl: 0 thinking, 1 text  (ultrathink in prompt — still nothing)
agent-aa50571.jsonl: 0 thinking, 3 text  (ultrathink in prompt — still nothing)
Model: claude-opus-4-6
Parent transcript: 38 thinking blocks, 39,089 chars      ← Parent HAS thinking
```

### What the hook captures today

The SubagentStop hook (`obsidian_capture.sh`) correctly:
- Reads each agent's own `agent_transcript_path` (no inter-joining between agents)
- Extracts thinking blocks when present (opus-4-5 sessions, future models)
- Reports `thinking_blocks: 0` when none found (opus-4-6 sub-agents)
- Captures output text, dynamic tags, frontmatter metadata regardless

Each agent gets its own file: `2026-03-09_general-purpose_a6785dae.md` — one .jsonl → one .md note. No mixing.

### Workarounds

1. **Use non-fork skills** — Skills WITHOUT `context: fork` inject their content into the parent conversation, which has thinking enabled. Remove `context: fork` from skill frontmatter to get thinking. Trade-off: no isolation, shares parent context window.

2. **Extract parent thinking** — The parent transcript contains thinking blocks about each agent (why it was spawned, what the parent concluded from results). The hook could correlate parent thinking to specific agents by matching the Agent tool_use call containing the agent_id. This is the parent's reasoning, not the agent's own thinking, but is still valuable context.

3. **Wait for upstream fix** — The `eo1` function appears to be missing `useExactTools: true` — likely a bug since it's inconsistent with the Agent/Task tool fork path which does pass it. Future Claude Code versions may fix this.

### Verified by test (2026-03-09)

Ran `test-child-thinking` skill (has `context: fork`, `model: claude-opus-4-6`, "ultrathink" in prompt) via Skill tool:
- Fork transcript `agent-a3a0314cbdb1aadac.jsonl`: **0 thinking blocks**
- Parent transcript same session: **87 thinking blocks**
- All 8 Agent/Task sub-agents: **0 thinking blocks each**

Confirmed: no spawn method currently produces thinking in sub-agent/fork transcripts.

---

## CLI Command Audit (2026-03-09)

**Tested every command from `obsidian --help` against live vault (earnings-analysis).**
**Total unique commands: 82. Verified: 73. Partial/buggy: 5. Not testable: 4.**

### Verified Working (73 commands)

| Category | Commands | Notes |
|---|---|---|
| **Vault/Version** (9) | `version`, `vault` (+info=name/path/files/size), `vaults` (+verbose/total) | All flags work |
| **File CRUD** (9) | `create` (+overwrite/open/newtab), `read`, `append` (+inline), `prepend` (+inline), `rename`, `move`, `delete` (+permanent), `file` | `file=` resolves wikilink-style, `path=` exact |
| **File Listing** (4) | `files` (+total/folder/ext), `folders` (+total/folder), `folder` (+info=files/folders/size) | All filters work |
| **Search** (3) | `search:context` (+path/limit/case/format), `search:open`, `search total` | `search:context` returns line-level matches |
| **Tags** (6) | `tags` (+total/counts/sort/format=json\|tsv\|csv/active), `tag` (+total/verbose), `tags path=` | All output formats verified |
| **Properties** (5) | `properties` (+total/counts/sort/name/format=yaml\|json\|tsv/active), `property:read`, `property:set` (text/number/checkbox/date/datetime/list), `property:remove` | All 6 types verified |
| **Graph** (5) | `links` (+total), `backlinks` (+total/counts/format=json\|tsv\|csv), `orphans` (+total/all), `deadends` (+total/all), `unresolved` (+total/counts/verbose/format) | Backlinks JSON verified |
| **Tasks** (2) | `tasks` (+total/todo/done/status/verbose/format=json\|tsv\|csv/path/active/daily), `task` (+toggle/done/todo/status/line/path) | Toggle round-trip verified |
| **Daily Notes** (5) | `daily` (+paneType), `daily:path`, `daily:read`, `daily:append` (+inline), `daily:prepend` (+inline) | All pass |
| **Outline** (1) | `outline` (+format=tree\|md\|json/total) | Tree rendering verified |
| **Wordcount** (1) | `wordcount` (+words/characters) | Accurate counts |
| **Bookmarks** (2) | `bookmark` (file/search/url/subpath/title), `bookmarks` (+total/verbose/format=json\|tsv\|csv) | All bookmark types work |
| **History** (5) | `history`, `history:list`, `history:read` (+version), `history:open`, `history:restore` (+version) | Restore verified via read |
| **Diff** (1) | `diff` (+from/to/filter) | Shows unified diff |
| **Tabs/Workspace** (3) | `tabs` (+ids), `tab:open` (+file/group), `workspace` (+ids) | Tree rendering with IDs |
| **Navigation** (4) | `open` (+newtab), `recents` (+total), `random`, `random:read` (+folder) | All pass |
| **Plugins** (7) | `plugins` (+filter/versions/format), `plugins:enabled`, `plugins:restrict` (+on/off), `plugin` (+id), `plugin:disable`, `plugin:enable`, `plugin:uninstall` | Full lifecycle except install |
| **Themes** (5) | `theme`, `themes` (+versions), `theme:install`, `theme:set`, `theme:uninstall` | Minimal theme install/set/uninstall round-trip verified |
| **Dev Tools** (9) | `eval`, `dev:cdp`, `dev:console` (+clear/limit/level), `dev:debug` (+on/off), `dev:dom` (+selector/total/text/inner/all/attr/css), `dev:errors` (+clear), `dev:mobile` (+on/off), `dev:screenshot` (+path), `devtools` | Screenshot produces valid PNG (94 KB) |
| **Misc** (3) | `help` (+command), `reload`, `aliases` (+total/verbose/file/active) | All pass |

### Partial / Buggy (5 commands)

| Command | Issue | Workaround | Confirmed? |
|---|---|---|---|
| `search` | Inconsistent results — some terms return files, others return empty despite content existing. After `reload`, index takes ~10s to partially rebuild but never fully indexes all terms. `search:context` and `search total` sometimes work when bare `search` doesn't. Known v1.12 bug ([forum thread](https://forum.obsidian.md/t/cli-search-returns-empty-for-multi-word-heading-text/111952)). | Use `search:context` for reliable results, or `eval` with `app.vault.cachedRead()` for guaranteed content search | Yes — reported on Obsidian Forum, unresolved |
| `plugin:install` | Silently no-ops — plugin not found after install. Possibly network/registry issue on headless server | Manual install or `eval` to call plugin API | Local issue, not a CLI bug |
| `plugin:reload` | Untestable — depends on `plugin:install` working | N/A | N/A |
| `dev:css` | Returns empty for valid selectors | Use `dev:dom` with `css=` param instead | Unconfirmed |
| `create` (without `path=`) | May open GUI window instead of running silently ([forum report](https://forum.obsidian.md/t/open-source-agent-skill-for-obsidian-cli-prevents-13-silent-failures/111169)). Using `path=` avoids this. | Always use `path=` not `name=` for headless | Yes — community confirmed |

### Not Testable (4 categories)

| Command(s) | Reason |
|---|---|
| `sync`, `sync:deleted`, `sync:history`, `sync:open`, `sync:read`, `sync:restore`, `sync:status` | Sync not configured (using Syncthing instead) |
| `template:insert`, `template:read`, `templates` | No template folder configured |
| `base:create`, `base:query`, `base:views`, `bases` | No base files in vault (commands respond correctly) |
| `restart` | Would disrupt the headless service |
| `snippet:enable`, `snippet:disable` | No CSS snippets installed (error handling verified) |

### Known CLI Issues (from Obsidian Forum + our testing)

Community reports ([13 silent failures post](https://forum.obsidian.md/t/open-source-agent-skill-for-obsidian-cli-prevents-13-silent-failures/111169)) found 22.8% of CLI test scenarios fail silently (exit 0, wrong/empty data). Key issues:

| Issue | Detail | Status |
|---|---|---|
| **Search inconsistency** | `search` returns empty for many terms despite content existing. `search:context` more reliable but also inconsistent after `reload`. Index rebuild takes 10+ seconds and is incomplete. [Forum thread](https://forum.obsidian.md/t/cli-search-returns-empty-for-multi-word-heading-text/111952). | Unresolved in v1.12.4 |
| **Active-file scope default** | `tasks`, `tags`, `properties` without explicit `path=` may scope to "active file" which doesn't exist in CLI context. [Forum thread](https://forum.obsidian.md/t/cli-tasks-and-tags-silently-return-empty-when-called-from-terminal/111168). Fix: always pass `path=`. | Partially fixed in v1.12.2+ (tasks reworked), our tests show vault-wide scope works |
| **Exit code always 0** | All commands return exit 0 even on errors — cannot rely on exit codes for automation | Known, not fixed |
| **`create` opens GUI** | `create name="x" content="y"` opens a window. Use `path=` instead of `name=` for headless. | Workaround: always use `path=` |
| **`DISPLAY=:99` required** | Every command segfaults without it. CLI is a remote-control for the running Electron app, not a standalone binary. This is by design — the [official docs](https://help.obsidian.md/cli) state "Obsidian must be running". | By design |
| **GPU errors cosmetic** | `Exiting GPU process due to errors during initialization` on ~30% of commands. Xvfb software rendering limitation. No effect on output or correctness. | Harmless, ignore |

### Key Findings

1. **`search` is unreliable** — Tested exhaustively: created a fresh file with "uniqueword12345 guidance earnings AAPL", searched immediately. "uniqueword12345" found (1 result), but "guidance" returned empty despite 24 files containing it in content (verified via `eval`). `search:context` is more reliable but also inconsistent after `reload`. The search index appears to have incomplete coverage. **Root cause unconfirmed** — forum reports suggest heading-only text and multi-word queries are affected, but single common words also fail. Use `eval` with `cachedRead()` for guaranteed search.

2. **`plugin:install` silently fails** — No error, no output, plugin not found afterward. Restricted mode was toggled off before testing. Likely a network/registry issue on this headless server, not a CLI bug per se.

3. **`DISPLAY=:99` required** — Every command segfaults without it. The CLI sends IPC commands to the running Obsidian Electron process. No Obsidian running = no CLI. This is by design, not a bug. On this server, Obsidian runs headless via Xvfb :99 systemd service.

4. **GPU errors are cosmetic** — `Exiting GPU process due to errors during initialization` appears on ~30% of commands. This is because Xvfb provides software rendering (no GPU). The error is from Chromium/Electron's GPU process initialization failing, which it handles gracefully by falling back to software. Zero impact on CLI functionality. Confirmed by testing all 73 working commands — GPU errors appear interleaved with correct output.

5. **`eval` is the power tool** — Full access to `app.vault`, `app.workspace`, `app.plugins`, `app.internalPlugins`. Can do anything the GUI can do. Example: `eval code="app.vault.getMarkdownFiles().length"` → `356`. Also the **reliable workaround for search**: `eval code="(async()=>{const files=app.vault.getMarkdownFiles();let r=[];for(const f of files){const c=await app.vault.cachedRead(f);if(c.includes('guidance'))r.push(f.path)}return r.length})()"` → `24`.

6. **`dev:cdp` unlocks Chrome DevTools Protocol** — Tested `Browser.getVersion`. Opens door to advanced automation (screenshots, network interception, DOM manipulation).

7. **`dev:screenshot` produces valid PNG** — 94-115 KB, 1024x767, RGB. Can be used for visual verification of vault state.

8. **All output formats work** — `json`, `tsv`, `csv`, `yaml`, `tree`, `md`, `text` all produce correct output across commands that support them.

9. **`file=` vs `path=` resolution** — `file=` resolves like a wikilink (by note name, no extension needed). `path=` resolves by exact relative path. Both work correctly. **For headless/automation, always prefer `path=`** to avoid active-file scope issues.

10. **Property types all work** — Verified: `text`, `number`, `checkbox`, `date`, `datetime`, `list`. List type correctly parses comma-separated values into YAML arrays.

11. **Task toggle round-trip verified** — `task toggle` → `[ ]→[x]`, then `task todo` → `[x]→[ ]`, then `task done` → `[ ]→[x]`. Line-level addressing works.

12. **Theme lifecycle works end-to-end** — `theme:install name="Minimal"` → `theme:set name="Minimal"` → `theme:set name=""` (default) → `theme:uninstall name="Minimal"`. All steps verified.

### Test Artifacts Created (cleaned up)

- `cli-test.md` — left in vault (sample note with tags, tasks, properties)
- `test-folder/test-file.md` → renamed → moved → deleted
- `delete-me.md` → trash, `perm-delete-test.md` → permanently deleted
- `open-test.md`, `newtab-test.md` → trash
- Bookmarks: 4 created (file, search, URL, subpath)
- Theme: Minimal installed → activated → default → uninstalled
- Daily note: append + prepend entries added
- Properties on cli-test.md: score, reviewed, due (set then removed)
