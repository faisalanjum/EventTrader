# Extraction Pipeline — Consolidated Tracker

Single source of truth for all done/open/future items across the extraction pipeline.

**Updated**: 2026-03-09 (all 5 asset profiles decontaminated; runtime error fixes E1/E4a/E4b DONE via warmup_cache.py)

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

### Full Asset Decontamination (3 Requirements)

All 5 generic asset profiles decontaminated to the same standard: (1) any new extraction type works without new queries, (2) zero guidance-specific content in generic files, (3) guidance extraction remains immediately executable.

| Item | Commit | Status |
|------|--------|--------|
| News: `news.md`, `news-queries.md` decontaminated; `news-primary.md` absorbs fulltext/withdrawn rules | `42ebdf6` | DONE |
| Control plane: `trigger-extract.py`, `extraction_worker.py` — static `ALLOWED_TYPES` → dynamic `discover_allowed_types()` | `42ebdf6` | DONE |
| 10-Q/10-K: `10q.md`, `10k.md` decontaminated; query 5I added for generic section access; `s.content_length` type fixed | `6c626d6` | DONE |
| 10-Q/10-K: `10q-primary.md`, `10k-primary.md` absorb basis inheritance, filing text fallback, section exclusions | `6c626d6` | DONE |
| Runtime: concept/member cache + transcript fetch routed through `warmup_cache.sh` to avoid MCP truncation | `6c626d6` | DONE |
| Runtime: `guidance_write_cli.py` diagnostic hint for nested-vs-flat JSON mistakes | `6c626d6` | DONE |
| 8-K: `8k.md`, `8k-queries.md` decontaminated; `8k-primary.md` absorbs content strategy, table columns, safe-harbor proximity | `4f5d7c3` | DONE |
| Transcript: `transcript.md` decontaminated; `transcript-primary.md` absorbs basis context trap | `4f5d7c3` | DONE |

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
| 10 | Query 2B Cypher syntax error | RESOLVED (`warmup_cache.py`) — query text in queries-common.md is valid Cypher. Runtime error was agent transcription fidelity failure: premature `dim_u_id AS axis_u_id` alias one WITH clause too early. Fixed by routing warmup to Bash helper that runs query verbatim via Bolt. |
| 11 | Enrichment agent missing `Edit` tool | NOT APPLICABLE — enrichment workflow uses Write only, never Edit. |

---

*All contagion categories (A/B/C/E) resolved. All 5 asset profiles (news, 10q, 10k, 8k, transcript) fully decontaminated.*

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
| C2 | Enrichment pass result schema inconsistency | Low | DONE | Agent shell result field now matches SKILL.md (`new_secondary_items`). SOURCE_TYPE note remains moot (`d3af160`). |

---

## Future Work

| Item | Source | Blocked On | Notes |
|------|--------|------------|-------|
| Phase 4: First non-guidance type | Pipeline plan S8 | Type selection | 5-6 files (auto-discovered via `discover_allowed_types()`) |
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
| E1 | **Agent query mutation — `dim_u_id` not defined** | Medium | Every run | DONE — agent prematurely aliases `dim_u_id AS axis_u_id` at line 27 of 52-line query 2B (verified in agent transcript vs queries-common.md:148). Fixed by `warmup_cache.py` Bash helper — agents no longer transcribe the query. Pass briefs updated to point at `warmup_cache.sh` instead of QUERIES.md 2A/2B. |
| E2 | **Nested envelope schema drift** | Medium | 2x | HARDENED — agent produced nested `{"company":{},"source":{},"items":[]}` instead of flat envelope. Partially fixed by explicit example in `enrichment-pass.md:80-92`. CLI error message now includes diagnostic `hint` field detecting nested objects. |
| E3 | **Member matching fallback warnings** | Low | Multiple | MONITORING — "resolved N items via code fallback". CLI does authoritative member matching via direct Neo4j query, overwriting LLM-provided member_u_ids. Working as designed. |
| E4a | **Cache truncation (warmup queries)** | Low | Not observed for AAPL | DONE — warmup caches (2A ~30KB, 2B ~40KB for AAPL) now fetched via `warmup_cache.py` Bash helper, bypassing MCP entirely. Prevents truncation for companies with larger XBRL profiles (>50KB). |
| E4b | **Transcript content truncation (query 3B)** | Low | Every transcript run | DONE — AAPL transcripts are 54-62KB, exceeding SDK ~50KB persisted output threshold. `transcript-primary.md` updated to always fetch via `warmup_cache.sh --transcript`, bypassing MCP. |

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
| `10q-decontamination.md` | **ARCHIVE** | Fully implemented (`6c626d6`). |
| `total-contagion-fix.md` | **ARCHIVE** | Fully implemented (`84fc97f`). |
| `transcript-guidancePollutionFix.md` | **ARCHIVE** | Fully implemented (`8a87a0f`). Recipe extracted to pipeline plan. |
| `extraction-pipeline-audit.md` | **DELETE** | All items absorbed into this tracker. |
| `axiom-purity-analysis.md` | **ARCHIVE** | Design proof. 7 unique items merged into Design Notes above. |
| `asset-guidancePollutionAudit.md` | **DELETE** | Per-asset pollution absorbed into this tracker with exact line numbers. |

---

*Consolidated 2026-03-07; updated 2026-03-08 (10-K split `d3af160`, contagion fix `84fc97f`, news.md fixup, tracker cleanup). Updated 2026-03-09 (full decontamination: news `42ebdf6`, 10q/10k `6c626d6`, 8k/transcript `4f5d7c3`).*
