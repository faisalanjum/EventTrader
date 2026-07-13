# Driver Catalog Seed — KPI → verbatim-quote linking

**Read this file first. It is the complete entry point — you need no other context.**
Repo root: `/home/faisal/EventMarketDB`. Run anything that touches Neo4j with
`venv/bin/python` (the system python lacks the `neo4j` driver). Neo4j creds are in `.env`
(`NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD`).

---

## What this is (plain terms)

We take every KPI from **fiscal.ai** (revenue by segment, unit counts, per-unit metrics,
organic-growth components, etc. — see `[[reference_fiscal_ai_kpi_data]]`) and link each one to
the **exact verbatim quote** in the company's SEC filings/transcripts stored in Neo4j that
states that value for that period.

This is the **RAW SEED INPUT** for the owner's Driver Catalog — the input the pipeline would
consume for any source. It is **NOT** built Drivers or DriverUpdates. Do not create Drivers.

**Hard rule: 100% precision.** A record is emitted only if its exact value is *literally present
in its quote*, at a numeric boundary, losslessly. Abstaining (no record) is correct and expected
when the value isn't in the filing.

---

## How it works — 3 tiers + 1 gate

1. **Code Tier-1 (XBRL, 0 tokens):** match an XBRL fact by value + period + dimension member.
   Deterministic and member-verified (e.g. `NewVehiclesMember = 2,825,640,000`).
2. **Code Tier-2 (text label, 0 tokens):** match a value form in filing text with the KPI's
   label tokens next to it, at a numeric boundary.
3. **LLM Tier-3 (residual):** an agent binds the leftovers. Two variants exist (see below).
4. **Deterministic value-gate (`merge_part.py`):** every record — code AND LLM — is emitted only
   if `link_lib.value_ok(value, fmt, quote)` passes. This is the real 100%-precision guarantee;
   no LLM can bypass it.

**Derived rows are dropped:** ~62% of fiscal.ai rows are `% Chg.` and `Common Size` — fiscal.ai
*computes* these (e.g. `-4.72705985657837%`); no filing ever states them, so they can never have a
verbatim quote and are excluded.

---

## Read these to understand it 100% (in order)

| # | File | What it is |
|---|------|-----------|
| 1 | `/home/faisal/.claude/projects/-home-faisal-EventMarketDB/memory/project_fiscal_ai_kpi_quote_linking.md` | Full state, every decision, every bug found & fixed |
| 2 | `scripts/driver_seed/link_lib.py` | **The heart** — tiers + gates. Has a runnable self-check (`venv/bin/python scripts/driver_seed/link_lib.py`) |
| 3 | `scripts/driver_seed/build_worklist.py` | Builds the work-list: fiscal.ai values ∩ Neo4j filings |
| 4 | `scripts/driver_seed/run_code_tier.py`, `prep_llm_batches.py`, `merge_part.py` | The pipeline: code tier → batch residual → merge+gate |
| 5 | `scripts/driver_seed/batched_llm_bind.js` (old), `snippet_bind.js` (new) | The two LLM-tier variants (see decision below) |
| 6 | `part1/seed_records.csv` | **The actual output** — open in a spreadsheet |

---

## What a record looks like (the deliverable)

`part1/seed_records.jsonl` / `.csv`, one row per `(ticker, kpi, period)`:

```
ticker=AAPL  kpi="iPhone Revenue"  value=201183000000  period=2024-09-28  form=10-K
tier=T1-xbrl  quote="iPhone $ 201,183"  filing_id=0000320193-24-000123
```

Columns: `ticker, kpi, value, fmt, period, form, filing_id, tier, source, member, concept, quote`.

---

## Current status

- **Part 1 of 4 partly done. ~3,390 records banked**, 153 companies. Parts 2–4 not started.
- Scope: 73,267 addressable KPI values across 1,413 company-periods, 633 companies
  (fiscal.ai ∩ Neo4j). Neo4j runs ~1 quarter behind fiscal.ai; missing periods auto-abstain.
- Precision: code tier ~100% (audited), old LLM tier 100% (audited + gate).

### ⚠️ OPEN DECISION (this is where the project is paused)

Two LLM-tier variants, both real, pick one before running Parts 2–4:

| | `batched_llm_bind.js` (old) | `snippet_bind.js` (new — CHOSEN) |
|---|---|---|
| method | read whole filing, extract **and** verify | bind from code-pre-located snippets, then cheap verify |
| cost | ~200K tokens / company-period | ~120K on the biggest batches (median batch is ~7 KPIs → lower avg) |
| audited precision | **100%** | **100%** (after the header-capture fix below) |

**RESOLVED (2026-07-12): the cheap pipeline now audits 100%.** Path taken:
1. Drop derived rows (`% Chg`, `Common Size`) — 62% of the work-list, never linkable.
2. Return the FULL chosen candidate as the quote (not a hand-clip).
3. Add a light verify pass (re-judges "right line?" from the quote text; no filing read).
4. **Header-capture fix** (`link_lib._snippet_start`): the candidate snippet now reaches back to
   include the KPI's own segment-name tokens, so a tall reconciliation table's HEADER row is
   captured together with the VALUES row. This closed the 91%→100% gap.

Re-audit after the fix: **102/102 correct (100%)** — the skeptic even reconstructed OCR-scrambled
multi-row headers via arithmetic column checks.

**Caveat:** this probe skewed toward a few companies (CAG, CMCSA, AFL) and the largest batches.
The result is strong but not yet a broad multi-company audit. Recommended: sample-audit ~50
records per part as Parts 1–4 run, don't assume.

### Cost levers — QUALITY-SAFE, proven, NOT yet live

Workflow agent calls carry big fixed harness overhead. Measured (trivial-task probe):
`general-purpose` (all tools) ~53K context/call vs a 2-tool agent ~34K → **strip unused tools = ~37%
less context, ZERO quality change** (same answer). Un-removable floor ~34-40K = the Claude Code
"uniform" (a `claude -p` probe confirmed `--allowedTools ""` does NOT remove it — use a lean AGENT
TYPE, `.claude/agents/lean-probe.md`, not tool-gating). Safe levers, in adoption order:
1. **lean agent type** (~37% context) · 2. **keep the prompt cache warm** — run chunks back-to-back
within the 1h TTL (a warm read is ~5-10× cheaper than a cold write) · 3. return candidate INDEX not
the full quote (cuts output).
**Status: NOT live.** `snippet_bind.js` default is still `general-purpose`; `agent_type` arg is the
switch. Blocked to a FRESH session (registry snapshots at startup) + must re-verify identical
bindings on a real batch first. **NOT safe:** downgrading to Haiku (moves recall/precision).

### Cost (MEASURED) + effort decision — LOCKED

- **Effort = `high` for both bind+verify** (locked 2026-07-12). A/B tested `medium`: only ~9% cheaper
  but −8% recall → rejected. Token cost is dominated by the candidate EVIDENCE, not reasoning, so
  no cheap lever preserves both precision AND recall. Pipeline is at its cost floor. Do NOT lower
  effort without a fresh recall+precision A/B.
- **Measured cost:** ~89K tokens per company-period at `high`.
- **Finish Part 1:** ~267 batches left → ~24M tokens.
- **Whole catalog:** ~1,370 residual company-periods → ~121M tokens (subscription; ~8 session windows).

### Next step (agreed direction)

Run the remaining work with `snippet_bind.js` (effort `high`) in chunks that fit the session token
cap (~16M/window), merge + value-gate after each chunk, then audit ONLY the non-self-sufficient
residual (`fix_quotes.py` detector) before certifying — that residual audit is what catches
coincidental small-value mis-bindings (13 found & removed in Part 1).

**⚠️ Session token limit is the binding constraint.** The full job is ~30–200M tokens depending on
variant and won't fit one session — run in chunks of ~70 company-period batches and **merge after
every chunk** so a limit hit never loses work.

---

## Run recipe (per part)

```bash
venv/bin/python scripts/driver_seed/build_worklist.py            # once, all parts
venv/bin/python scripts/driver_seed/run_code_tier.py   --part N  # code tiers -> partN/
venv/bin/python scripts/driver_seed/prep_llm_batches.py --part N # group residual per company-period
# then run snippet_bind.js (or batched_llm_bind.js) via the Workflow tool on partN/llm_batches.json,
# in chunks: {path, idx:[...]}  or  {path, lo, hi}
venv/bin/python scripts/driver_seed/merge_part.py --part N --llm-output <task .output files...>
venv/bin/python scripts/driver_seed/recall_report.py --part N    # real recall vs correct-abstentions
```

**Do not run anything yet — read, confirm understanding, then state the open decision above and
your recommendation.**
