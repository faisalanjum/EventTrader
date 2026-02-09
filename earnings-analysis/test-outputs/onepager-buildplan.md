## Build Plan & Existing Assets

### Reusable Assets (exist, working)

- **guidance-inventory skill v1.6** — Production-ready data skill with `QUERIES.md`, `OUTPUT_TEMPLATE.md`, `FISCAL_CALENDAR.md`. Runs as Step 0 per ticker; ~80% reusable, needs orchestrator bridge hardening (I5: raw markdown passthrough) and G1-G8 question resolution.
- **11 data sub-agents** in `.claude/agents/` — Neo4j (report, transcript, xbrl, entity, news), Alpha Vantage (earnings), Perplexity (search, ask, reason, research, sec), plus `guidance-extract`. All exist and are functional but need PIT-compliance rework (JSON envelope, `available_at` fields per `DataSubAgents.md`).
- **`get_quarterly_filings.py`** — Working discovery script. Feeds Step 1 (event.json generation).
- **`build_orchestrator_event_json.py` hook** — Auto-builds `event.json` from filing discovery output.
- **Evidence standards + Neo4j cookbooks** — Shared reference files for citation and query patterns.

### Must Build From Scratch

| Component | Why |
|-----------|-----|
| **Planner skill** (`.claude/skills/earnings-planner/SKILL.md`) | New module — reads 8-K + U1 feedback, emits `fetch_plan.v1` JSON. Single-turn, no data fetching. |
| **`pit_gate.py` + `pit_fetch.py`** | PIT enforcement layer — fail-closed gate for historical mode. Every data query routes through this. Foundation dependency. |
| **Context bundle renderer** | Converts `context_bundle.v1` JSON to sectioned text for Skill invocation (~20 lines, deterministic). |
| **`build_summary.py`** | Aggregation: reads per-quarter `result.json` files into summary CSV. Explicitly not orchestrator scope. |
| **Inline validation logic** | 5 deterministic rules (confidence_bucket from score, magnitude_bucket from move range, signal derivation, horizon enforcement, move range precision). Code-only, no LLM call. |

### Must Rewrite

- **Orchestrator skill** — 4 of 8 steps are placeholders; needs full wiring of planner, data fan-out, predictor, and attribution loop with file-authoritative state.
- **Predictor skill** — Wrong output schema (doesn't match `prediction_result.v1`), wrong tool access (still allows `Task`, `Skill`, `filtered-data` — must be bundle-only with `Read/Write/Glob/Grep/Bash` only).
- **Attribution/Learner skill** — ~10% aligned with plan. Fundamental redesign: new `attribution_result.v1` schema, U1 feedback block (`what_worked/what_failed/why/predictor_lessons/planner_lessons`), autonomous data fetching (no pre-assembled bundle), and Phase 2 multi-model readiness.

### Recommended Build Order

1. **`pit_gate.py` + `pit_fetch.py`** — Foundation; everything depends on PIT enforcement.
2. **Reference agent rework** — Use `neo4j-news` as template; add JSON envelope + `available_at` to all 11 agents.
3. **Planner skill** (new) — Unblocks predictor testing via `fetch_plan.v1` generation.
4. **Predictor skill rewrite** — Lock tool access, implement `prediction_result.v1`, add inline validation.
5. **Orchestrator skill rewrite** — Wires planner + data fan-out + predictor + validation. Core integration point.
6. **Learner skill rewrite** — Biggest effort, least dependency on others. New schema + U1 feedback loop.
7. **Guidance integration hardening** — Resolve G1-G8, lock BUILD/UPDATE trigger, verify sub-files.
8. **`build_summary.py` + consistency pass** — Aggregation tooling + cross-module contract verification.
