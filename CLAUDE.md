# EventMarketDB — Project Instructions

## User Communication Rules — how to talk to me (READ FIRST — every reply, incl. after compaction/resume)

**Before sending ANY message, check:** *"Would a brand-new person with zero context get this in one read?"* If no → rewrite. I read fast and forget fast (treat me like I have ADHD). These rules beat your default style and are permanent.

1. **Plain words.** No jargon. If a technical/project term is unavoidable, define it in ~5 plain words the first time.
2. **Short, but complete.** A few sentences by default. Cut filler — never cut real information.
3. **Crux first.** Lead with the answer. One idea per line. Short bullets. Clear next step. No wall of text.
4. **Show, don't tell.** Use small visuals when faster than words: mini-tables, arrows (A → B), before/after.
5. **Refresh my memory.** Before leaning on earlier context, remind me in one line (e.g. *"Reminder: X worked, Y failed"*).
6. **Explain before the writeup.** Start any proposal/plan/spec with plain what / why / what-I'm-proposing, THEN the detail.

For Driver work: say the goal in plain terms BEFORE files, tests, or plans. Never bury the point in history.

**When unsure how a Claude Code tool or CLI behaves:** check `.claude/plans/Infrastructure.md` first — don't guess.

> **Recap:** crux first · plain words · few sentences (but complete) · small visuals · refresh my memory · explain before writeup.

## Anthropic API Key Handling (CRITICAL — read before editing SDK/LLM code)

> 📌 **Billing survival guide (June 15 2026 subscription change, no-charge proof, EarningsTrigger/Guidance fix recipe, Option #6):** see **`.claude/plans/ANTHROPIC_BILLING_SUBSCRIPTION_CRITICAL.md`** — canonical, empirically tested. Read it before changing any `claude_agent_sdk` / `claude -p` entrypoint.

> 📌 **Driver AI experiments:** before any reader, table-disambiguation, transcript,
> token, or cost run, read FinalPlan Phase 6. It is the sole current authority for
> the local AI + Haiku/Sonnet/Luna candidate pool, testing bar, escalation, and
> owner approval. This is only a pointer; do not create a second policy here.

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
Only the ARCHIVED legacy driver scripts (moved 2026-07-15: `archive/drivers/` — e.g., `archive/drivers/drivers_graph/*.py`, `archive/drivers/agenticDrivers/mcpAgent.py`). They use the direct Anthropic SDK and require the raw key. The NEW driver system (repo-root `driver/`) never uses the raw key — subscription lanes only.

To run an archived legacy driver that needs the key:
```bash
source ~/.anthropic_drivers_key && python3 archive/drivers/drivers_graph/mcp_agent_v2.py
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

## EarningsCall API Key — TEMPORARILY DISABLED (2026-05-16)

**`EARNINGS_CALL_API_KEY` is disabled in TWO places on purpose** (sub lapsed 2026-05-03; the `trade-ready` cron jobs were calling the API ~4×/weekday → "unauthorized access" dunning). With no key the `earningscall` lib falls to demo mode → raises locally **before any network call** → zero traffic. News/SEC/Polygon unaffected (different keys). Intentional, not broken.

Status (`.env` alone covers the email cause; `.bashrc` covers manual runs):
1. **`.env` line 15 — commented ✅** (`#EARNINGS_CALL_API_KEY=…`). Covers the K8s cron pods (they run `python3` directly, do NOT source `.bashrc`, no key in pod env) → demo mode → zero calls. **This stops the dunning emails** (cron jobs were the autonomous caller). Verified via pod-env simulation.
2. **`~/.bashrc` line 18 — commented ✅** (`#export EARNINGS_CALL_API_KEY="…"`, done 2026-05-16 via backup+temp+`cp`, NOT `sed -i`). Covers host/manual/interactive runs. Verified: clean shell sourcing `~/.bashrc` → key UNSET. Already-open shells still hold the in-memory var until `unset EARNINGS_CALL_API_KEY` or restart.

> 🛑 **DO NOT run `sed -i` (or any automated edit tool) on `~/.bashrc` in this environment.** On 2026-05-16 `sed -i` truncated `~/.bashrc` to 0 bytes (the `.env` `sed -i` worked, but `.bashrc` does not — likely a secrets-file write guard). Recovered from `~/.bashrc.bak.neo4j-cleanup-20260424-182350`. To change `~/.bashrc`, edit it by hand in an editor (`nano`), and make a timestamped backup first.

Still latent (deferred, needs kubectl): `EARNINGS_CALL_API_KEY` in the K8s `eventtrader-secrets` Secret — event-trader's source. event-trader is down + Polygon-gated, so dormant; clear it before redeploying event-trader.

### To restore (after re-subscribing at earningscall.com)
Uncomment `.env` line 15 (delete the leading `#`) — that alone restores the cron-pod path; no redeploy/rebuild/kubectl (cron pods read `.env` fresh each run). `~/.bashrc` line 18 is already active so host runs work too. If you rotated the key, use the new value.

### Notes
- Also rotate the key at earningscall.com when convenient (it was exposed in a terminal session 2026-05-16).
- For a *total* stop when event-trader is redeployed, also clear `EARNINGS_CALL_API_KEY` from the K8s `eventtrader-secrets` Secret (needs kubectl; deferred — event-trader is currently down and Polygon-gated anyway).

---
