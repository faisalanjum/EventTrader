# Extraction Pipeline — Consolidated Tracker

Single source of truth for all done/open/future items across the extraction pipeline.

**Updated**: 2026-03-08 (10k split + SOURCE_TYPE removal landed; total contagion fix landed; first production run complete)

---

## Completed

### Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1.1 | Asset profile files from PROFILEs | DONE |
| 1.2 | Split QUERIES.md into three-tier query files | DONE |
| 1.3 | Type contract + pass files for guidance | DONE |
| 1.4 | Two generic agent shells | DONE |
| 1.5 | `/extract` orchestrator skill | DONE |
| 1.6 | Baseline validation (golden checks) | DONE |
| 2.1 | `trigger-extract.py` | DONE |
| 2.2 | `extraction_worker.py` | DONE |
| 2.3-2.5 | K8s setup + canary + E2E validation | DONE |
| 3.0 | Evidence-standards as 7th auto-load (12-line universal rules, correct scoping) | DONE |
| 3.1-3.5 | Multi-asset validation (all 5 asset types) | DONE |

### Pollution Fixes

| Item | Commit | Status |
|------|--------|--------|
| Layer A: `transcript.md` — guidance extraction rules removed | `8a87a0f` | DONE |
| Layer B: `transcript-queries.md` L48 — guidance description | `8a87a0f` | DONE |
| Layer C: `queries-common.md` L55/112/206 — guidance comments | `8a87a0f` | DONE |
| `enrichment-pass.md` — 29 lines genericized (Q&A → secondary) | `8a87a0f` | DONE |
| `guidance-queries.md` 7E description updated | `8a87a0f` | DONE |
| `guidance-queries.md` 7F parameterized (`source_type`) | `8a87a0f` | DONE |
| `SKILL.md` gate — sections → file-existence | `8a87a0f` | DONE |
| Agent shells — slot 4, "working brief", dynamic file count | `8a87a0f` | DONE |
| Intersection files created: `transcript-primary.md`, `transcript-enrichment.md` | `8a87a0f` | DONE |

### 10-K Asset Split + SOURCE_TYPE Removal

| Item | Commit | Status |
|------|--------|--------|
| 10-K split into standalone asset (`10k.md`, `10k-queries.md`) | `d3af160` | DONE |
| SOURCE_TYPE parameter removed from all files | `d3af160` | DONE |
| 10q.md cleaned of 10-K references | `d3af160` | DONE |
| 4F/4G/4C query gap fixed | `d3af160` | DONE |
| Dead `form_type` removed from trigger-extract.py query results | `0d544dc` | DONE |

### Total Contagion Fix (Categories A/B/C/E)

| Item | Commit | Status |
|------|--------|--------|
| Category A: `queries-common.md` — Item 2.02 filter removed from 8A, execution order genericized | `84fc97f` | DONE |
| Category B: `primary-pass.md` — routing table, transcript scope, news filter, JSON example all genericized | `84fc97f` | DONE |
| Category B: `core-contract.md` — field examples, routing table, source type mapping, empty-content rules all genericized | `84fc97f` | DONE |
| Category C: Corporate announcements reversed (extract → exclude, dividend exception kept) in primary-pass, enrichment-pass, core-contract, transcript-primary, transcript-enrichment | `84fc97f` | DONE |
| Category E: `8k.md`, `news.md`, `10q.md`, `10k.md` — guidance-specific content removed/genericized | `84fc97f` | DONE |
| Category E: Query files (`news-queries.md`, `10q-queries.md`, `10k-queries.md`) — descriptions genericized | `84fc97f` | DONE |
| 4 intersection files created: `8k-primary.md`, `news-primary.md`, `10q-primary.md`, `10k-primary.md` | `84fc97f` | DONE |
| `transcript-primary.md` — source fields table, MCP truncation workaround, section field added | `84fc97f` | DONE |
| `transcript-enrichment.md` — 3C fallback provenance note added | `84fc97f` | DONE |
| Phase 7.5: `section` field + richness bias removal across all intersection files | `84fc97f` | DONE |

### First Production Run (5 AAPL transcripts)

| Item | Status |
|------|--------|
| 5 AAPL transcripts extracted (2023-02 through 2024-02) | DONE |
| 46 GuidanceUpdate nodes written, all graph links correct | DONE |
| KEDA parallel scaling (1→4 pods) verified | DONE |

### Resolved S11 Items

| # | Item | Resolution |
|---|------|------------|
| 5 | evidence-standards loading | 7th auto-load, post-parity (Phase 3.0) |
| 7 | Asset `sections` declaration format | Markdown `## Asset Metadata` with `- sections:` |
| 9 | Enrichment pass JSON envelope format | Explicit example added to `enrichment-pass.md` |
| 10 | Query 2B Cypher syntax error | INVALID — query is syntactically correct. Runtime error was Neo4j version quirk, agents work around it. |
| 11 | Enrichment agent missing `Edit` tool | NOT APPLICABLE — enrichment workflow uses Write only, never Edit. |

---

*All contagion categories (A/B/C/E) resolved — see Completed section above.*

---

## Implementation Deviations (from audit)

| # | Deviation | Impact |
|---|-----------|--------|
| 1 | Frozen originals were ARCHIVED (moved to `.claude/archive/`) instead of kept in-place as plan said "never moved" | Low — files accessible, just different location. Affects: `guidance-extract.md`, `guidance-qa-enrich.md`, `guidance-transcript/SKILL.md`, `trigger-guidance.py`, `earnings_worker.py` |
| 2 | `evidence-standards.md` is a 12-line local copy at `extract/evidence-standards.md`, not the 46-line original at `.claude/skills/evidence-standards/SKILL.md` | Low — agents load the 12-line version. 34 lines of additional context not seen by extraction agents. |

---

## Resolved — Top Note #2: Corporate Announcements

**Status**: DONE (`84fc97f`). Reversed from "ARE extractable" to "Do NOT extract" with dividend exception. All 5 locations updated (primary-pass, enrichment-pass, core-contract, transcript-primary, transcript-enrichment). Buyback/investment/facility announcements excluded; dividend-per-share guidance kept as extractable.

---

## Open — S11 Items (Still Active)

| # | Item | Status | Priority |
|---|------|--------|----------|
| 1 | GuidancePeriod: share across types? | DEFERRED | Phase 4 |
| 2 | Budget/cost optimization | OPEN | Low |
| 3 | `earnings_trigger.py` retirement check | PENDING | Confirm dormant |
| 4 | core-contract.md too long (733 lines) | DEFERRED | Post-retirement |
| 6 | Rename `{type}-inventory` convention | POST-RETIREMENT | — |
| 8 | Shared `write_cli.py` abstraction | Phase 4+ | Only if >50% shared |

---

## Open — Quick Wins (1-line frontmatter changes)

| # | Item | Effort | Benefit |
|---|------|--------|---------|
| 14 | `includeGitInstructions: false` on both agents | 1 line each | Saves ~500 tokens/turn |
| 19 | `argument-hint` on `/extract` SKILL.md | 1 line | Autocomplete help |
| 20 | `disable-model-invocation: true` on `/extract` | 1 line | Saves ~100 tokens |
| 22 | `disallowedTools: [mcp__neo4j-cypher__write_neo4j_cypher]` on both agents | 1 line each | Defense-in-depth safety |

---

## Open — Enhancements (Larger Effort)

| # | Item | Status | Notes |
|---|------|--------|-------|
| 12 | `${CLAUDE_SKILL_DIR}` for portable paths | OPEN | v2.1.69+. Only in SKILL.md, agents still need project-relative paths. |
| 13 | `agent_type` in hooks for per-agent validation | OPEN | v2.1.69+. `jq` check at top of each hook script. |
| 15 | Per-company agent memory (`memory: project`) | OPEN | Two-tier design in S11.15. Shared MEMORY.md + per-company `{TICKER}.md`. |
| 16 | `model:` field for cost optimization | OPEN | Primary=opus, enrichment=sonnet. Requires variant agents or SDK override. |
| 17 | `PostToolUseFailure` hook for error monitoring | OPEN | Structured error logging without transcript parsing. |
| 18 | `skills:` field to auto-load evidence-standards | OPEN | Saves 1 Read call per invocation. |
| 21 | Stop hook as final quality gate on `/extract` | OPEN | Validates result file before returning. Saves full retry cost. Complex. |

---

## Open — Prompt / Contract Gaps

| # | Issue | Severity | Status | Notes |
|---|-------|----------|--------|-------|
| C1 | Transcript 3C fallback sub-provenance | Medium | DONE | `transcript-enrichment.md:84` documents 3C fallback: "For 3C fallback (QuestionAnswer nodes): use `qa.id` directly — no sequence available." `primary-pass.md` is now asset-generic and defers per-asset `source_refs` format to the intersection file, so no unresolved transcript-specific provenance gap remains in the active prompt stack. |
| C2 | Enrichment pass result schema inconsistency | Low | OPEN | Concrete mismatch between agent shell and SKILL.md result field names (`new_items` vs `new_secondary_items`). Not worker-breaking. Note: SOURCE_TYPE references in stale docs are now moot (SOURCE_TYPE removed in `d3af160`). |

---

## Future Work

| Item | Source | Blocked On | Notes |
|------|--------|------------|-------|
| Phase 4: First non-guidance type | Pipeline plan S8 | Type selection | 5-6 files + whitelist entries |
| Generic extraction type for learner | Pipeline plan (OPEN section) | `learner.md` implementation | Copy guidance schema → Generic/GenericUpdate/GenericPeriod. Learner edits 1 file. |
| Learner-triggered job spawning | — | Generic type + trigger design | Learner adds extraction tasks on-the-fly to generic type. Needs trigger mechanism that supports both auto-ingestion triggers AND learner-initiated ad-hoc triggers. See Trigger Design below. |
| Shared `write_cli.py` abstraction | Pipeline plan S11 #8 | Phase 4 (type #2 reveals pattern) | Only if >50% code shared |
| Retirement of old worker/trigger | Pipeline plan (Cleanup section) | Quality-gated | `kubectl delete` old claude-code-worker |
| Obsidian integration for agent artifacts | — | Design needed | Primary/enrichment agents write full JSON payloads (all extracted items with every field: label, values, quotes, periods, etc.) to `/tmp/gu_{TICKER}_{SOURCE_ID}.json` and `/tmp/gu_{TICKER}_{SOURCE_ID}_enrichment.json`. These are ephemeral and lost on pod restart. Fix: save to persistent, organized storage — per-company folder (e.g., `extractions/AAPL/`) and/or per-job-type folder (e.g., `extractions/guidance/`), integrated with Obsidian vault so payloads, dry-run diffs, and thinking tokens are browsable/searchable alongside notes. |
| Sonnet vs Opus output comparison | — | `model:` field working | Run same extraction with `model: sonnet` and `model: opus`, diff output quality. Determines cost-performance tradeoff per agent role (primary vs enrichment) and per asset complexity (transcript vs news). |
| Trigger design for multi-source job creation | — | Generic type setup | Current triggers: auto on ingestion (`trigger-extract.py --all`), manual per-source (`--source-id`), per-ticker. Need: learner-initiated triggers (learner updates pass file, then triggers extraction across relevant sources), scheduled re-extraction (cron-based), event-driven (new data ingested → auto-queue for all registered types). Design should unify all trigger paths into one mechanism. |

---

## Known Runtime Issues (from actual AAPL runs)

Issues observed during production extraction runs. Non-fatal but worth tracking.

### Errors to Fix

| # | Issue | Severity | Frequency | Status |
|---|-------|----------|-----------|--------|
| E1 | **Recurring Cypher syntax error — `dim_u_id` not defined** | Medium | Every run (all workers) | OPEN — query 2B (member profile cache) hits `Variable dim_u_id not defined` on every worker during warmup. Not just enrichment — primary agents also hit it. Agents always self-recover by retrying with corrected syntax. Likely MCP tool mangles the backtick escaping in the multi-line Cypher. Query is syntactically correct in Neo4j browser. Non-fatal but wastes ~1 turn per agent. |
| E2 | **"Missing required top-level fields" JSON envelope errors** | Medium | 2x | OPEN — agent produced malformed JSON missing `source_id`, `source_type`, `ticker`. Both times self-corrected on retry. Explicit envelope example was added to `enrichment-pass.md` (2026-03-06) but may still occur with new sources. |
| E3 | **Member matching fallback warnings** | Low | Multiple | MONITORING — "resolved N items via code fallback". Member matcher couldn't find exact XBRL matches, fell back to fuzzy/code-based resolution. Not an error but watch for accuracy drift. |
| E4 | **MCP output truncation → JSON parse tracebacks** | Low | 2x per batch | OPEN — MCP tool returns truncated output for large query results (member cache, concept cache). Agent's inline Python JSON parse fails with traceback. Self-healing: agents re-fetch via Bash+Python to `/tmp` and parse from file. Non-fatal but wastes 1-2 turns per occurrence. |

### Not Bugs (Confirmed Working-As-Designed)

| # | Observation | Explanation |
|---|-------------|-------------|
| N1 | **Revenue "duplicates" — 5 GUs for same period** | Correct: per-segment guidance (iPhone, iPad, Mac, Services, Total). ID includes member suffix (`:iphone`, `:mac`), so records are distinct. Working as designed. |
| N2 | **`metric_value` is null on many GUs** | Expected for qualitative guidance ("similar to last year", "low single digits"). Worth auditing periodically to confirm no numeric guidance was missed, but null is the correct value when no number is given. |

---

## Design Notes (from axiom-purity analysis)

Unique insights preserved from design proofs:

1. **PASS is subordinate to TYPE** — not an independent 3rd axis. Each type defines its own pass set. Model is: 2 independent axes (TYPE x ASSET) + TYPE-defined phases.
2. **Hyphen naming constraint** — asset names must not contain hyphens (collision with `-{pass}` delimiter in `{ASSET}-primary.md`). Use underscores.
3. **>2 sections limitation** — if a future asset has 3+ content sections, extend enrichment pass to handle multiple secondary sources (Option 1) or add tertiary pass (Option 2). Current 2-pass model handles all existing assets.
4. **Intersection files are optional by design** — not every TYPE x ASSET combo needs one. Missing-but-needed files caught by dry-run regression (Gate 2), not file-loading mechanism.
5. **Cross-type data sharing** — no mechanism exists. Correctly handled at orchestrator level, not instruction files. Prevents pollution by design.
6. **File proliferation is linear** — worst case: N types x M assets x P passes. 3 types x 5 assets = ~25 intersection files max. Not exponential.

---

## Source Files Disposition

| File | Verdict | Reason |
|------|---------|--------|
| `extractionPipeline_v2.md` | **KEEP** (primary plan) | Architecture + recipe + phases |
| `extraction-pipeline-tracker.md` | **KEEP** (this file) | Consolidated tracking |
| `extraction-instruction-stack.md` | **KEEP** (operational ref) | Unique: what each agent actually sees, message types, context accounting |
| `10k-split-source-type-removal.md` | **ARCHIVE** | Fully implemented (`d3af160`). |
| `total-contagion-fix.md` | **ARCHIVE** | Fully implemented (`84fc97f`). |
| `transcript-guidancePollutionFix.md` | **ARCHIVE** | Fully implemented (`8a87a0f`). Recipe extracted to pipeline plan. |
| `extraction-pipeline-audit.md` | **DELETE** | All items absorbed into this tracker. |
| `axiom-purity-analysis.md` | **ARCHIVE** | Design proof. 7 unique items merged into Design Notes above. |
| `asset-guidancePollutionAudit.md` | **DELETE** | Per-asset pollution absorbed into this tracker with exact line numbers. |

---

*Consolidated 2026-03-07; updated 2026-03-08 (10-K split `d3af160`, contagion fix `84fc97f`, news.md fixup, tracker cleanup).*
