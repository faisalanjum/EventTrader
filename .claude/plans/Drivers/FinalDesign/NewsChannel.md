# NewsChannel.md — the `analyst_news` channel

> **Status: LIVE (owner-approved 2026-07-16). Decisions only — one section per decision, added as approved.**
> Rule meaning lives in `FINAL_DESIGN.md`; channel duties in `ChannelContract.md`. This file holds only news-channel decisions.

## D1 — Filter models

Every item is read by a model; labels only route, never exclude.
Chain: Haiku 4.5 (Claude sub) → GPT-5.6 Luna (Codex sub) → DeepSeek V4 Flash (API); fall through on failure or rate-limit.
Always call with a **zero-tool agent** (`tools: []`) — this cuts harness overhead 10× (27,735 → 2,932 tokens/item).
`effort=high` — measured equal quality to low/medium and cheapest (low rambles).
Live (~230/day, one at a time): Haiku, ~674K tokens/day, subscription. Backfill (349K): DeepSeek, $13 one-time.
Measured on 32 hard cases: Haiku caught 15/16 buried facts, 0 false alarms — beating Sonnet (14/16).
