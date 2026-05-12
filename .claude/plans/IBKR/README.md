# IBKR — plans index

All IBKR (Interactive Brokers) MCP documentation lives here. Two active references, one archived.

## Files

| File | Purpose |
|------|---------|
| [`deployment.md`](deployment.md) | **K8s / runbook side** — pods, ports, secrets, image rollback pins (smart-fix-1 ↔ ext-hours-v3), rebuild flow, recovery procedures, 2FA notes |
| [`capabilities.md`](capabilities.md) | **Functional reference** — 25 tools, scanner cheat sheet (619 codes), recipes, subscription gates, known bugs, **§7b canonical IV methodology** |
| [`archive/gateway-reliability.md`](archive/gateway-reliability.md) | Historical (~Apr 2026) — gateway-stability plan (Login Messages, 2FA, daily restart). Superseded by smart-fix-1 baseline + K8s Recreate strategy. Kept for forensics. |

## Cross-references outside this folder

- `~/.claude/projects/-home-faisal-EventMarketDB/memory/project_ibkr_market_data.md` — subscription rationale, rejection list, future-subscription candidates, historical-data matrix, IV-methodology pointer
- `~/.claude/projects/-home-faisal-EventMarketDB/memory/MEMORY.md` — index entry pointing back here

## Quick lookup — where to find common questions

```
"Which subscriptions should I buy?"                → memory/project_ibkr_market_data.md
"How do I rebuild + redeploy the MCP?"             → deployment.md "Rebuild" section
"How do I roll back?"                              → deployment.md "Rollback Image Pin" section
"What tools does the MCP expose?"                  → capabilities.md §1
"What works / what doesn't?"                       → capabilities.md §2
"How do I compute IV for a stock?"                 → capabilities.md §7b
"How do I find liquid earnings names via scanner?" → capabilities.md §3 + §4
"Known bugs?"                                      → capabilities.md §6
```
