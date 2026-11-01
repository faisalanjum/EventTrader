# Obsidian vault search — the reliable path for agents

**TL;DR — to find notes in the vault, call `vault_search.py`. Never use `obsidian search`.**

## Why this exists

Obsidian's built-in search is **broken** on this headless host (v1.12.4). Verified 2026-06-17:
the word `guidance` is in **2,931** vault notes, yet every built-in path returned **nothing**:

| path | result |
|---|---|
| `obsidian search query=...` | empty ❌ |
| `obsidian search:context` | empty ❌ |
| `obsidian search total` | empty ❌ |
| `obsidian eval` + `cachedRead()` | empty ❌ (old "known-good" workaround no longer works) |
| **`vault_search.py` (ripgrep on disk)** | **2,931 in ~15 ms ✅** |

A built-in search that returns empty + exits `0` makes an agent **silently conclude the info
isn't there.** This helper reads the actual `.md` files with ripgrep — ground truth, no Obsidian
index, no running app required.

## Use it

```bash
# human-readable
python3 scripts/obsidian/vault_search.py "same store sales"

# machine-readable (agents: parse JSON, trust `count`, NOT the exit code)
python3 scripts/obsidian/vault_search.py --json "guidance"

# only match inside YAML frontmatter (e.g. find notes whose metadata mentions a ticker/type)
python3 scripts/obsidian/vault_search.py --frontmatter "type: prediction"

# show the matching lines, regex, limit
python3 scripts/obsidian/vault_search.py --content --regex "EPS\s+\$[0-9]" --limit 10
```

Options: `--vault PATH` (or `$OBSIDIAN_VAULT`) · `--regex` · `--case-sensitive` ·
`--frontmatter` · `--content` · `--limit N` · `--json`.

JSON shape: `{ok, engine, query, vault, frontmatter, count, returned, results:[{path, abs_path,
matches, snippet, lines}]}`. `count` is the **true total**; `results` is the top `--limit` by
match count.

> For ranked relevance inside an agent that already has MCP, `mcp__obsidian__search_notes` (BM25)
> also works and is fine. This script is the universal, app-independent default that any agent
> with Bash can call.

## Keep it from regressing

```bash
bash scripts/obsidian/check_broken_search.sh   # flags any code that calls the broken search
python3 scripts/obsidian/test_vault_search.py  # deterministic tests vs the live vault
```

`check_broken_search.sh` exits non-zero if any executable code (`.sh`/`.py`/`.bash`) calls
`obsidian search*` — wire it into CI to keep the broken path out for good.

## Scope / what this does NOT touch

Purely additive. It does **not** modify the capture hook, `.mcp.json`, `obsidian.json`, the
headless service, or any skill/agent. It only **adds** a read-only search tool.
