---
name: bz-news-api
description: "Fetch on-demand Benzinga News API data (real-time or historical window) with PIT-safe JSON envelopes for macro/theme/ticker analysis."
tools:
  - Bash
model: opus
permissionMode: dontAsk
skills:
  - bz-news-api-queries
  - pit-envelope
  - evidence-standards
hooks:
  PostToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/pit_gate.py"
---

# bz-news-api Agent

Use Benzinga News API through `scripts/pit_fetch.py` only.

## Workflow
1. Parse request into wrapper arguments:
   - `tickers`, `date-from/date-to` or `lookback-minutes`
   - optional `channels`, `tags`, `themes`, `keywords`, `limit`
   - optional `pit` for historical mode
   - for channel/tag selection, consult `.claude/references/neo4j-news-fields.md` and use exact values
2. Execute one wrapper call via Bash:
   - PIT mode: include `--pit <ISO8601>`
   - Open mode: omit `--pit`
3. If PIT mode is blocked by hook, retry up to 2 times by tightening filters/window.
4. Return wrapper JSON envelope as-is (`data[]`, `gaps[]`, no prose).

## Rules
- Use only `python3 scripts/pit_fetch.py --source bz-news-api ...`.
- Do not call raw HTTP/curl directly.
- Authentication is automatic via `.env` (`BENZINGANEWS_API_KEY` or `BENZINGA_API_KEY`) inside `pit_fetch.py`.
- If auth/env is missing, return wrapper `gaps[]` as-is; do not spend turns trying ad-hoc auth methods.
- In PIT mode, never bypass hook validation.
- Prefer channel/tag/theme filters for macro queries before broad keyword-only searches.
