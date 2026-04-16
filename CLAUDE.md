# EventMarketDB — Project Instructions

## Anthropic API Key Handling (CRITICAL — read before editing SDK/LLM code)

**The `ANTHROPIC_API_KEY` is NOT in `.env` by design.** It was removed on 2026-04-16 after a root-cause analysis showed it was being silently injected into every `claude -p` subprocess spawned by `claude_agent_sdk`, causing ~$22/day of API charges that should have been covered by the user's Claude Code Max subscription.

### Where the key lives now
`~/.anthropic_drivers_key` (chmod 600, sourceable). Contains:
```
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

### Do NOT
- **Do NOT** add `ANTHROPIC_API_KEY` back to `.env`. Auto-loading via `load_dotenv()` will reintroduce the leak.
- **Do NOT** `export ANTHROPIC_API_KEY=...` in global shell profiles (`.bashrc`, `.zshrc`, `.profile`) for the same reason.
- **Do NOT** use the Anthropic Python SDK (`import anthropic`) for new code that does LLM inference. Use the Claude Code SDK instead (`claude_agent_sdk`) so calls go through the user's OAuth subscription.

### Who needs the key
Only `drivers/` directory scripts (e.g., `drivers/drivers_graph/*.py`, `drivers/agenticDrivers/mcpAgent.py`). They use the direct Anthropic SDK and require the raw key.

To run a driver that needs the key:
```bash
source ~/.anthropic_drivers_key && python3 drivers/drivers_graph/mcp_agent_v2.py
```

### Who does NOT need the key
- **Everything using `claude_agent_sdk`** — it uses the system `claude` CLI at `~/.local/bin/claude` which authenticates via OAuth (`~/.claude/.credentials.json`). Subscription billing, not API.
- **K8s workers** (`k8s/processing/*.yaml`) — they explicitly set `ANTHROPIC_API_KEY: ""` to force OAuth.
- **The earnings pipeline** (`scripts/earnings/earnings_orchestrator.py`) — has fail-closed guards that strip `ANTHROPIC_API_KEY` from env before SDK calls, even if something upstream sets it.

### If you're writing new LLM code
Use `claude_agent_sdk.query()` with `ClaudeAgentOptions(cli_path="/home/faisal/.local/bin/claude")` and rely on the user's OAuth subscription. Do NOT accept an API key as input. Reference pattern: `scripts/earnings/earnings_orchestrator.py::_run_learner_via_sdk()`.

### If a driver script stops working
It's probably missing the env var. Source `~/.anthropic_drivers_key` first.

---
