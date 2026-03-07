# Extraction Pipeline — Consolidated Tracker

Single source of truth for all done/open/future items across the extraction pipeline.

**Updated**: 2026-03-07 (post-team-audit of 6 plan files)

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
| 3.1-3.5 | Multi-asset validation (all 4 asset types) | DONE |

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

### Resolved S11 Items

| # | Item | Resolution |
|---|------|------------|
| 5 | evidence-standards loading | 7th auto-load, post-parity (Phase 3.0) |
| 7 | Asset `sections` declaration format | Markdown `## Asset Metadata` with `- sections:` |
| 9 | Enrichment pass JSON envelope format | Explicit example added to `enrichment-pass.md` |
| 10 | Query 2B Cypher syntax error | INVALID — query is syntactically correct. Runtime error was Neo4j version quirk, agents work around it. |
| 11 | Enrichment agent missing `Edit` tool | NOT APPLICABLE — enrichment workflow uses Write only, never Edit. |

---

## Open — Remaining Pollution (8k/news/10q)

Transcript is clean. These 3 assets still have guidance-specific content in generic files. Follow the validated recipe in `extractionPipeline_v2.md` Section "Pollution Fix Recipe."

### 8k.md (199 lines) — 33 lines to fix

| Lines | Content | Action |
|-------|---------|--------|
| 61 | "richest source for 8-K guidance" | REWRITE → "richest source for 8-K content" |
| 76 | "rarely useful for guidance" | REWRITE → "rarely contains extractable content" |
| 80 | "yielded zero guidance" | REWRITE → "yielded zero extractable content" |
| 95 | "may mix actuals and guidance" | REWRITE → "mix actuals and forward-looking statements" |
| 96 | "concrete guidance" | REWRITE → "concrete forward-looking content" |
| 113-127 | "What to Extract" table | MOVE to `types/guidance/assets/8k-primary.md` |
| 130-136 | "Do NOT Extract" list | MOVE to `types/guidance/assets/8k-primary.md` |

### news.md (228 lines) — 73 lines to fix

| Lines | Content | Action |
|-------|---------|--------|
| 17 | "contains complete guidance" | REWRITE → "primary content" |
| 30, 37 | "HIGH/MODERATE guidance likelihood" | REWRITE → remove guidance labels |
| 34 | "Company forward-looking statements" | REWRITE → "Company statements" |
| 41 | "may include prior guidance" | REWRITE → "Pre-earnings analysis" |
| 75 | "contain complete guidance" | REWRITE → "complete forward-looking content" |
| 91 | "Prior guidance values" | REWRITE → "Prior values for context" |
| 99-111 | "What to Extract" table | MOVE to `types/guidance/assets/news-primary.md` |
| 114-143 | "Do NOT Extract" + analyst table | MOVE to `types/guidance/assets/news-primary.md` |
| 146-162 | "Reaffirmation Handling" | MOVE to pass file (news subsection) |
| 180 | "guidance became public" | REWRITE → "content became public" |
| 208-213 | "GuidanceUpdate" references | Generalize to "extraction item" |

### 10q.md (242 lines) — 45 lines to fix

| Lines | Content | Action |
|-------|---------|--------|
| 16 | "designated scan scope for guidance" | REWRITE → "for extraction" |
| 62 | "Zero guidance from a 10-K" | REWRITE → "Zero items from a 10-K" |
| 85 | "10-Q/10-K guidance" | REWRITE → "10-Q/10-K extraction" |
| 93 | "CapEx/FCF forward guidance" | REWRITE → "forward expectations" |
| 97 | "zero guidance" | REWRITE → "zero extractable content" |
| 100-103 | "guidance keywords" | REWRITE → "extraction keywords" |
| 107 | "Zero guidance" (repeated) | REWRITE → "Zero items" |
| 115, 119-120, 122 | "Guidance Likelihood" column | Generalize or remove |
| 124-138 | "What to Extract from MD&A" table | MOVE to `types/guidance/assets/10q-primary.md` |
| 141-147 | "Do NOT Extract" list | MOVE to `types/guidance/assets/10q-primary.md` |
| 165, 169, 171 | "guidance" in period/source sections | REWRITE → "content" |
| 183-185 | "Forward-Looking Strictness" quality rule | MOVE to pass file (10q subsection) |
| 236-237 | "Guidance frequency" in 10-K vs 10-Q table | Generalize |

### Query File Rewrites (descriptions only, zero Cypher changes)

| File | Lines | Action |
|------|-------|--------|
| `news-queries.md` | 17, 19, 51, 55 | 4 lines: "Guidance-Channel" → "Channel-Filtered", etc. |
| `10q-queries.md` | 22, 34, 51, 53 | 4 lines: "guidance extraction" → "extraction", etc. |
| `queries-common.md` | 308 | 1 line: "Guidance-channel news" → "Channel-filtered news" |

### Estimated Effort

| Asset | Rewrites | Tables to Move | Intersection Files to Create | Time |
|-------|----------|----------------|------------------------------|------|
| 8k | 6 lines | 2 (27 lines) | `8k-primary.md` | ~1h |
| news | 8 lines | 3 (65 lines) | `news-primary.md` | ~1.5h |
| 10q | 13 lines | 3 (32 lines) | `10q-primary.md` | ~1.5h |
| Query files | 9 lines | — | — | 15min |
| **Total** | **36 lines** | **8 tables** | **3 files** | **~4h** |

---

## Implementation Deviations (from audit)

| # | Deviation | Impact |
|---|-----------|--------|
| 1 | Frozen originals were ARCHIVED (moved to `.claude/archive/`) instead of kept in-place as plan said "never moved" | Low — files accessible, just different location. Affects: `guidance-extract.md`, `guidance-qa-enrich.md`, `guidance-transcript/SKILL.md`, `trigger-guidance.py`, `earnings_worker.py` |
| 2 | `evidence-standards.md` is a 12-line local copy at `extract/evidence-standards.md`, not the 46-line original at `.claude/skills/evidence-standards/SKILL.md` | Low — agents load the 12-line version. 34 lines of additional context not seen by extraction agents. |

---

## Open — Top Note #2: Corporate Announcements

**Status**: Documented, not yet fixed. Intentionally deferred — requires type separation design.

"Corporate announcements ARE extractable" exists in 3 files:
- `primary-pass.md` L92
- `enrichment-pass.md` L138
- `core-contract.md` (Material corporate announcements row)

**Required removals** (execute when ready to create separate `announcements` type):
1. Remove corporate-announcement examples from intersection files
2. Remove "ARE extractable" rules from both pass files
3. Remove "Material corporate announcements" row from core-contract.md
4. Add replacement: "Do NOT extract capital allocation announcements (separate type)"

**Impact boundary**: Keep dividend per share as guidance. Exclude buyback authorizations, investment programs, facility plans.

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

## Future Work

| Item | Source | Blocked On | Notes |
|------|--------|------------|-------|
| Phase 4: First non-guidance type | Pipeline plan S8 | Type selection | 5-6 files + whitelist entries |
| Generic extraction type for learner | Pipeline plan (OPEN section) | `learner.md` implementation | Copy guidance schema → Generic/GenericUpdate/GenericPeriod. Learner edits 1 file. |
| Learner-triggered job spawning | — | Generic type + trigger design | Learner adds extraction tasks on-the-fly to generic type. Needs trigger mechanism that supports both auto-ingestion triggers AND learner-initiated ad-hoc triggers. See Trigger Design below. |
| 10Q/10K asset split | Pollution fix plan (Future Work) | Pollution cleanup first | 6 edits + 2 creates. ASSET=source_type one-to-one. |
| Shared `write_cli.py` abstraction | Pipeline plan S11 #8 | Phase 4 (type #2 reveals pattern) | Only if >50% code shared |
| Retirement of old worker/trigger | Pipeline plan (Cleanup section) | Quality-gated | `kubectl delete` old claude-code-worker |
| Obsidian integration for agent artifacts | — | Design needed | Integrate Obsidian with all `/tmp` files agents write (JSON payloads, dry-run output, thinking tokens). Organized by task type, source, date. Makes agent work inspectable and auditable outside terminal. |
| Sonnet vs Opus output comparison | — | `model:` field working | Run same extraction with `model: sonnet` and `model: opus`, diff output quality. Determines cost-performance tradeoff per agent role (primary vs enrichment) and per asset complexity (transcript vs news). |
| Trigger design for multi-source job creation | — | Generic type setup | Current triggers: auto on ingestion (`trigger-extract.py --all`), manual per-source (`--source-id`), per-ticker. Need: learner-initiated triggers (learner updates pass file, then triggers extraction across relevant sources), scheduled re-extraction (cron-based), event-driven (new data ingested → auto-queue for all registered types). Design should unify all trigger paths into one mechanism. |

---

## Known Runtime Issues (from actual AAPL runs)

Issues observed during production extraction runs. Non-fatal but worth tracking.

### Errors to Fix

| # | Issue | Severity | Frequency | Status |
|---|-------|----------|-----------|--------|
| E1 | **Recurring Cypher syntax error — `dim_u_id` not defined** | Medium | 3x across runs | OPEN — enrichment agent generates a query referencing undefined variable. Recovers each time (non-fatal). Bug in enrichment query template, not in `queries-common.md` 2B (which is syntactically correct). Likely the agent constructs a derived query that drops the `WITH` binding. |
| E2 | **"Missing required top-level fields" JSON envelope errors** | Medium | 2x | OPEN — agent produced malformed JSON missing `source_id`, `source_type`, `ticker`. Both times self-corrected on retry. Explicit envelope example was added to `enrichment-pass.md` (2026-03-06) but may still occur with new sources. |
| E3 | **Member matching fallback warnings** | Low | Multiple | MONITORING — "resolved N items via code fallback". Member matcher couldn't find exact XBRL matches, fell back to fuzzy/code-based resolution. Not an error but watch for accuracy drift. |

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
6. **File proliferation is linear** — worst case: N types x M assets x P passes. 3 types x 4 assets = ~20 intersection files max. Not exponential.

---

## Source Files Disposition

| File | Verdict | Reason |
|------|---------|--------|
| `extractionPipeline_v2.md` | **KEEP** (primary plan) | Architecture + recipe + phases |
| `extraction-pipeline-tracker.md` | **KEEP** (this file) | Consolidated tracking |
| `extraction-instruction-stack.md` | **KEEP** (operational ref) | Unique: what each agent actually sees, message types, context accounting |
| `transcript-guidancePollutionFix.md` | **ARCHIVE** | Fully implemented (8a87a0f). Recipe extracted to pipeline plan. |
| `extraction-pipeline-audit.md` | **DELETE** | All items absorbed into this tracker. |
| `axiom-purity-analysis.md` | **ARCHIVE** | Design proof. 7 unique items merged into Design Notes above. |
| `asset-guidancePollutionAudit.md` | **DELETE** | Per-asset pollution absorbed into this tracker with exact line numbers. |

---

*Consolidated 2026-03-07 from 6-auditor team review of: extractionPipeline_v2.md, extraction-pipeline-audit.md, transcript-guidancePollutionFix.md, axiom-purity-analysis.md, asset-guidancePollutionAudit.md, extraction-instruction-stack.md.*
