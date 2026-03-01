# Guidance Extraction Issues — AAPL Transcripts (All 5 Runs)

## Open Items

| # | Issue | Priority | Status | Notes |
|---|-------|----------|--------|-------|
| 1 | Agent bypassed CLI write path — constructed raw Cypher via MCP write tool | CRITICAL | **Fixed** | Removed `write_neo4j_cypher` from tools. **Verified Run 6 (2026-02-26)**: 0 `write_neo4j_cypher` calls across all 10 agents (5 P1 + 5 P2). |
| 2 | Wrong MERGE pattern (ON CREATE SET for all props instead of SET) | CRITICAL | **Fixed** | Auto-fixed by #1 |
| 3 | 20 MCP write calls instead of 2 (Write JSON + Bash CLI) | CRITICAL | **Fixed** | Auto-fixed by #1 |
| 4 | Feature flag ENABLE_GUIDANCE_WRITES completely bypassed | Medium | **Fixed** | Auto-fixed by #1 |
| 5 | WHA missing MAPS_TO_MEMBER edge (should link to WHAMember) | Medium | **Fixed** | Prompt rewrite worked. Run 4 confirmed: WHA correctly linked to `WearablesHomeandAccessoriesMember`. All 5 segment items have MAPS_TO_MEMBER. |
| 6 | Segment Revenue items (5/6) missing MAPS_TO_CONCEPT edges | Medium | **Fixed** | Concept inheritance in `guidance_write_cli.py` (4 tests). Same label = same concept. |
| 7 | No Q&A synthesis — all 11 quotes from PR only, §15C ignored | Medium | **Fixed** | Single-agent 3a/3b/3c failed (Run 3: 3/10). Escalated to two-invocation: `guidance-extract` (PR) → `guidance-qa-enrich` (Q&A). Run 4: 5/10 enriched. See `two-invocation-qa-fix.md`. |
| 8 | iPad/WHA share evhash (f611c8fee63e3f44) — identical qualitative text | Low | **Closed** | By design — same directional guidance, null numerics, similar conditions → same value fingerprint. Separate nodes via segment in ID. |
| 9 | Peak context 105k tokens (81% window) — compaction risk on larger transcripts | CRITICAL | **Fixed** | Auto-fixed by #1 |
| 10 | FX Impact extracted as standalone item instead of Revenue condition | Low | **Fixed** | Added quality filter to SKILL.md §13: factors affecting a metric go in `conditions`, not as standalone items. **Regression in Issue #21** — same filter cited but overridden by recall priority on $900M tariff. |
| 11 | 3B query result too large for direct tool result — agent falls back to Bash+Python parsing | Low | **Won't-fix** | Cannot split 3B into PR-only query — Phase 1 uses Q&A as recovery fallback when PR is truncated (see #18: Revenue recovered from Q&A). Removing Q&A from fetch would break this safety net. Agent self-heals via Bash+Python on large transcripts (~30s). Added hint to agent prompt Step 2 so agent knows the workaround upfront. |
| 12 | Agent modified `config/feature_flags.py` directly with `sed -i` to enable writes | Medium | **Fixed** | Env var override added to `guidance_writer.py`. Agents now use `ENABLE_GUIDANCE_WRITES=true bash guidance_write.sh --write`. Process-scoped, no config file editing. |
| 13 | Phase 2 re-discovers feature flag toggle (~60s, 8 extra tool calls) | Low | **Fixed** | Auto-fixed by #12 — env var in Bash command, no discovery needed. |
| 14 | Stale /tmp JSON file collision in Phase 1 | Low | **Closed** | One-time occurrence. Write tool overwrites by default, so stale files cause no harm. No `/tmp/gu_*` files currently exist. The 15s overhead was agent over-caution, not a real bug. |
| 15 | Phase 2 skipped readback verification after write | Low | **Won't-fix** | CLI already returns structured JSON with `was_created`, edge linking results, and errors — agent parses this in Step 6. A post-write readback query is redundant (verifying the verifier). Phase 1's readback was agent improvisation, not a prompted step. No observed failure mode where CLI exit 0 was wrong across all 5 runs. |
| 16 | Guidance periods share `:Period` label with XBRL periods despite different schemas | Low | **Fixed** | Resolved by GuidancePeriod redesign (`guidance-period-redesign.md`). New `:GuidancePeriod` label with calendar-based `gp_` IDs. Old `guidance_period_` `:Period` nodes deleted. Run 6 confirmed: all items use `gp_` format GuidancePeriod nodes, no `:Period` label collision. |
| 17 | Phase 2 gave up on feature flag — Q&A enrichment computed but not persisted (DATA LOSS) | **CRITICAL** | **Fixed** | Escalation of #12/#13. Agents improvised different workarounds (sed-i, Python override, or gave up). Fixed: env var check in `guidance_writer.py` (lines 26-35), both agent prompts updated to `ENABLE_GUIDANCE_WRITES=true bash guidance_write.sh --write`. 62 tests pass. |
| 18 | Truncated PreparedRemarks node — CFO guidance section cut off mid-sentence | Medium | **Open (upstream)** | AAPL_2025-05-01 (Q3 FY2025): CFO section truncated at 6,782 chars before guidance numbers. Gross Margin, OpEx, OINE, Tax Rate lost. Revenue recovered from Q&A. Upstream data quality issue — not fixable in extraction pipeline. Scope unknown. Mitigation: softened Phase 1 "PR ONLY" to allow Q&A fallback when PR is truncated/empty (see #11). |
| 19 | `guidance-extractor` skill not in user-invocable registry — `/guidance-extractor` doesn't work | Low | **Fixed** | Moved bare file `.claude/skills/guidance-extractor.md` → `.claude/skills/guidance-extractor/SKILL.md`. Now registers and `/guidance-extractor` is invocable. |
| 20 | Unit double-scaling bug — agent pre-scales values AND sets unit_raw to "billion" | Medium | **Fixed** | Prompt fix: added "Copy the number and unit exactly as printed" rule to `guidance-extract.md` Step 3. Code guard: 2-line check in `canonicalize_value()` — rejects when `multiplier > 1 and value > 999` (nobody says "$1000+ billion"). 78 tests pass. |
| 21 | Tariff Cost Impact extracted as standalone despite citing quality filter (Issue #10 regression) | Medium | **Fixed** | Agent cited §13 factors rule, then recall priority overrode it. Fix: updated §13 factors row to eliminate the conflict — "A factor already captured in a metric's conditions field is already extracted — do not also create a standalone item for it." |
| 22 | P2-Q3FY2025 dropped Revenue enrichment — false "already enriched" claim | Medium | **Fixed** | Agent hallucinated "already enriched in prior run" to skip writing. Fix: added rule to `guidance-qa-enrich.md` — "Never skip an ENRICHES verdict. MERGE+SET handles idempotency." |
| 23 | P2-Q3FY2025 Q&A verdict inconsistency between analysis and report | Low | **Self-corrected** | #4 (Ben Ricey) downgraded from ENRICHES to NO GUIDANCE between initial analysis and final output. Final verdict more accurate, but silent reclassification harms auditability. |
| 24 | 2 of 3 guidance uniqueness constraints missing in Neo4j | Medium | **Fixed** | `create_guidance_constraints()` never run against live DB. Fixed: ran all 7 statements via MCP write tool. 3 constraints confirmed (Guidance existing, GuidanceUpdate + GuidancePeriod created). |
| 25 | 3 of 4 sentinel GuidancePeriod nodes missing | Medium | **Fixed (historical)** | Original fix was completed. Current recurrence is tracked as active Issue #44 to avoid duplicate open tracking. |
| 26 | Segment-qualified labels produce separate Guidance parents instead of grouping under base metric | Medium | **Fixed** | Root cause: §4 never referenced in agent prompt. Fix: rewrote §4 Metric Decomposition (business dimension vs. accounting modifier test), added §4/§7 reference to `guidance-extract.md` Step 3 and `guidance-qa-enrich.md` NEW ITEM path. Added non-exhaustive banner + inline one-liners at 5 high-risk sections. Zero code changes. |
| 27 | Services Revenue segment inconsistency — segment="Total" in 1 of 4 items | Low | **Fixed** | Fixed by #26 — §7 segment rules now explicitly referenced in agent prompt Step 3. Default segment="Total", set segment only for business dimensions. |
| 28 | `PER_SHARE_LABELS` too narrow — `adjusted_eps`, `non_gaap_eps` get `m_usd` instead of `usd` | Medium | **Fixed** | Replaced exact-match set with `_is_per_share_label()` pattern function (4 rules: exact `eps`/`dps`, startswith `eps_`/`dps_`, endswith `_eps`/`_dps`, contains `per_share`/`per_unit`). Added fail-closed guards in `_validate_item()`: Guard A rejects per-share label + `m_usd`, Guard B rejects xbrl_qname PerShare/PerUnit/PerDilutedShare/PerBasicShare + `m_usd`. Guards use `== 'm_usd'` (not `!= 'usd'`) to avoid false-rejecting qualitative and percentage EPS/DPS guidance. 151 tests pass. |
| 29 | PROFILE_TRANSCRIPT.md uses wrong derivation in example | Low | **Fixed** | Line 76: `derivation=calculated` → `derivation=explicit`. SKILL.md §5: explicit = company states exact range, calculated = derived from math. One-word doc fix. |
| 30 | Batch summary undercounts member/concept links on re-runs | Low | **Fixed** | Moved `concept_links`/`member_links` accumulation outside the `was_created` conditional in `write_guidance_batch()`. Now counts links on both creates and re-runs. |
| 31 | `derivation` silently defaults to `'implied'` in writer | Low | **Fixed** | Changed default from `'implied'` to `'unknown'` in `_build_params()`. `unknown` is not a valid §5 value, so any occurrence in DB immediately flags a missing-derivation extraction bug. Agent already sets derivation explicitly on every item. |
| 32 | Tariff Cost Impact extracted as standalone despite §13 factors rule (Issue #21 regression) | Medium | **Closed (won't-fix)** | LLM judgment call on ambiguous edge case. Downstream pipeline (planner/predictor) receives guidance as raw markdown passthrough — holistic LLM reasoning handles whether tariff is standalone or in conditions. Tightening spec risks overfitting. Data is captured either way. |
| 33 | DPS / Share Repurchase / US Investment Spending extracted as guidance | Low | **Closed (won't-fix)** | Capital allocation items are clearly labeled (label=Dividends Per Share, etc.) — downstream consumers filter trivially. Boundary is genuinely fuzzy (buyback auth is arguably forward guidance). Planner/predictor receive guidance as raw text and reason holistically — extra items are noise the LLM filters naturally. Adding prescriptive rules risks overfitting. |
| 34 | Transcript #4 took 8m01s (2-3x longer than others) with 41 tool calls | Low | **Closed (resolves with #18)** | Root cause: truncated PreparedRemarks (#18). CFO section cut off at 6,782 chars before guidance numbers. Agent spent ~20 extra tool calls searching the dead-end PR before Q&A fallback. Phase 2 ran at normal speed (3m07s, 16 calls). Not a code bug — expected recovery behavior on broken upstream data. Fix #18 (upstream truncation) and this resolves automatically. |
| 35 | Duplicate transcript IDs create duplicate GuidanceUpdate nodes | **HIGH** | **Open** | **Full DB audit (2026-03-01): 205 duplicate groups across 4,397 transcripts (9.3%).** Every group is exactly a pair — one short-format ID (`TICKER_YYYY_Q`) and one long-format ID (`TICKER_YYYY-MM-DDThh.mm.ss-TZ`) with identical `conference_datetime`. Pattern is 100% consistent (205/205 clean short+long pairs, zero triples). Both copies in each pair have identical child content (same PreparedRemarks count, same QAExchange count). 20 GuidanceUpdate nodes currently point to duplicates (all AAPL — the only company with extraction runs). Root cause is upstream ingestion: two separate loads used different ID conventions for the same earnings call. Fix options: (A) ingestion-time dedup, (B) extraction-time detection, (C) post-write cleanup query. Related quality inconsistency on duplicates tracked in #46. |
| 46 | Non-deterministic sentinel classification: capex `gp_UNDEF` vs `gp_LT` between duplicate runs | Medium | **Closed (resolves with #35)** | 9/10 matched pairs between duplicate sources are identical. Only CapEx drifted — genuinely ambiguous quote ("continue to see our CapEx grow") with no time horizon. LLM non-determinism on a 4-way judgment call, surfaced only because #35 creates two extraction runs on the same content. Fix duplicate transcripts → one run → one consistent classification. No spec or code change needed. |
| 36 | GuidanceUpdate FROM_SOURCE links only to Transcript — consider also linking to QAExchange | Low | **Fixed** | Added `source_refs` array property on GuidanceUpdate — stores sub-source node IDs (e.g., QAExchange IDs for transcripts). Generic, source-agnostic: works for any future sub-node type. No new edges or relationships needed. Writer passes through from agent JSON; defaults to `[]`. qa-enrich agent instructed to populate with `{SOURCE_ID}_qa__{sequence}` IDs. Queryable via `UNWIND gu.source_refs AS ref MATCH (qa:QAExchange {id: ref})`. |
| 37 | K8s portability blocker: write path defaults Neo4j URI to `bolt://localhost:30687` | Medium | **Open** | In pods, `localhost` is the pod itself, not Neo4j. `guidance_write.sh` default at `.claude/skills/earnings-orchestrator/scripts/guidance_write.sh:13`. Toy write-path run (2026-02-28) showed Phase 2 failure: connection refused. Cluster-safe URI candidate: `bolt://neo4j-bolt.neo4j.svc.cluster.local:7687`. |
| 38 | `guidance-qa-enrich` Step 6 hardcodes `--write` in example even when MODE is dry_run/shadow | Medium | **Fixed** | Replaced hardcoded `--write` example with MODE→flag mapping table + both dry-run and write examples, matching `guidance-extract.md` pattern. |
| 39 | Container runtime requirement not documented in guidance agents: `SHELL=/bin/bash` | Low | **Open** | Toy run v2 blocked both phases with Bash unavailable until `SHELL` was set. Not a logic bug in guidance extraction, but an execution contract gap for K8s jobs. Should be documented in deployment requirements for guidance agents. |
| 40 | K8s runner must execute as non-root for `--dangerously-skip-permissions` flows | Medium | **Open** | Claude CLI rejects `--dangerously-skip-permissions` under root. Enforce `runAsNonRoot: true`, `runAsUser: 1000`, `runAsGroup: 1000` in guidance job templates. |
| 41 | MCP reliability requires explicit `--strict-mcp-config` in guidance jobs | Medium | **Open** | Toy runs showed MCP tool availability drift without strict config loading. Standardize `--strict-mcp-config` for guidance skill/subagent executions to avoid missing tool errors. |
| 42 | Runtime image strategy unresolved when GHCR pulls fail (`403`) | Medium | **Open** | `ghcr.io/cabinlab/claude-agent-sdk:python` was not pullable anonymously in-cluster. Need a committed strategy: imagePullSecret for GHCR OR supported fallback runtime image (`node:20` + npm install) with pinned version/perf baseline. |
| 43 | Missing repeatable pre-prod canary for full two-phase guidance path | Medium | **Open** | Add one deterministic canary with explicit phase contract: (A) run `MODE=write` (Phase 1 + Phase 2) in isolated namespace with cleanup, or (B) pre-seed Phase 1 rows first, then run `MODE=dry_run` to validate Phase 2 behavior. `MODE=dry_run` alone cannot prove full two-phase success because Phase 2 depends on 7E readback from Phase 1 writes. |
| 44 | Sentinel GuidancePeriod nodes `gp_ST` and `gp_MT` missing after Run 7 (Issue #25 regression) | Medium | **Fixed** | Root cause: `create_guidance_constraints()` was never re-run after clean-slate wipe. Fix: `guidance_write_cli.py` now calls `create_guidance_constraints(manager)` at the start of every write-mode batch. Idempotent (7 no-op queries, ~50ms). Sentinels auto-created on every write run — survives any future wipe. |
| 45 | Run 7 aggregate totals are internally inconsistent with per-transcript table and live DB | Low | **Closed (stale)** | The "45 P1 + 6 P2 = 51" claim exists only in this issue description. The actual post-mortem table (lines 144-147) says 43+4=47, matching DB (47 nodes) and per-transcript arithmetic. Stale description from a draft that was corrected. No data bug. |
| 47 | Write-path credentials hardcoded with plaintext password in `guidance_write.sh` | Medium | **Open** | `guidance_write.sh:14-16` force-sets `NEO4J_USERNAME=neo4j`, `NEO4J_PASSWORD=Next2020#`, `NEO4J_DATABASE=neo4j` as defaults. #37 covers URI only. In K8s, credentials must come from Secrets via `GUIDANCE_NEO4J_USERNAME`, `GUIDANCE_NEO4J_PASSWORD`, `GUIDANCE_NEO4J_DATABASE` env vars. The override mechanism exists (same `${GUIDANCE_..:-default}` pattern as URI) but the plaintext password in the script is a security concern for any shared/committed repo. **Validate:** set all 4 `GUIDANCE_NEO4J_*` env vars from a K8s Secret, confirm write path connects successfully. |
| 48 | Write-mode Python import chain requires heavy dependencies not guaranteed in container | Medium | **Open** | `guidance_write_cli.py:223` in `--write` mode does `from neograph.Neo4jConnection import get_manager` → `Neo4jManager` → imports `config.feature_flags`, `XBRL.xbrl_core`, `pandas`, `tenacity`, `neo4j` driver. If the container's Python version mismatches the host venv (e.g., container Python 3.12 vs venv built on 3.11), or if any dependency is missing, write path fails at import time. Dry-run mode is unaffected (no DB connection needed). **Validate:** run `--write` mode in container, confirm no `ImportError` or `ModuleNotFoundError` from the `neograph` → `XBRL` → `config` chain. |
| 49 | K8s MCP config must name server exactly `neo4j-cypher` | Medium | **Open** | Both guidance agents declare `mcp__neo4j-cypher__read_neo4j_cypher` in their tools list (`guidance-extract.md:6`, `guidance-qa-enrich.md:6`). The MCP tool name is `mcp__{server-name}__read_neo4j_cypher`. If the K8s `--mcp-config` JSON names the server `neo4j` or `mcp-neo4j` instead of `neo4j-cypher`, all read queries in Steps 1-3 fail (tool not found). This naming constraint is documented in `ClaudeCodeonKubernetes.md` and should be enforced here as a hard requirement. #41 covers config drift, not naming mismatch. **Validate:** create K8s ConfigMap with `{"mcpServers": {"neo4j-cypher": {...}}}`, confirm agents can call `mcp__neo4j-cypher__read_neo4j_cypher` from inside pod. |
| 50 | `guidance_write_cli.py` hardcodes absolute path `/home/faisal/EventMarketDB` | Low | **Open** | `guidance_write_cli.py:60-61`: `sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts")` and `sys.path.insert(0, "/home/faisal/EventMarketDB")`. K8s plan mitigates via exact-path hostPath mount, but if mount path ever changes, CLI fails with `ModuleNotFoundError` on `guidance_ids` and `guidance_writer`. Fragile — should use relative path from `__file__` instead. **Validate:** confirm the hostPath mount at `/home/faisal/EventMarketDB` makes CLI importable; separately, consider patching to `os.path.dirname(os.path.abspath(__file__))` for portability. |
| 51 | `CLAUDE_PROJECT_DIR` env var is recommended for container portability (not strictly required for guidance-only path) | Low | **Open** | Guidance extraction can still work when `workingDir` is correct and absolute hook paths are valid, but `CLAUDE_PROJECT_DIR` is strongly recommended for consistent project resolution across the broader agent/skill set (especially paths that use `$CLAUDE_PROJECT_DIR`). Set `CLAUDE_PROJECT_DIR=/home/faisal/EventMarketDB` in K8s for consistency. **Validate:** run `claude -p` in container with and without `CLAUDE_PROJECT_DIR`, confirm guidance skill/agents still resolve in both cases and broader project hooks/scripts behave as expected. |
| 52 | `u_id` is null on all 47 GuidanceUpdate nodes | Medium | **Closed (not-a-bug)** | Spec §1 defines `u_id` only on GuidancePeriod, not GuidanceUpdate. GU uses `id` as both MERGE key and reference. No `u_id` convention on GU. |
| 53 | `label` and `label_slug` are null on all 47 GuidanceUpdate nodes | HIGH | **Fixed** | Spec stored `label` on Guidance parent only — GU had no denormalized copy. Added `gu.label`, `gu.label_slug`, `gu.segment_slug` to writer SET block + params (defensive `or slug()` fallback). Spec §1 updated. 154 tests pass. Next write-mode run populates all 47 nodes via MERGE+SET. |
| 54 | `direction` is null on all 47 GuidanceUpdate nodes | Medium | **Closed (not-a-bug)** | `direction` appears zero times in SKILL.md spec. Field was never designed or specified. New feature would require enum design, extraction prompt changes, validation. |
| 55 | `segment_raw` and `segment_slug` are null on all segmented GuidanceUpdate nodes | Medium | **Fixed** | `segment` (raw) was already stored 47/47. `segment_slug` added as denormalized property for efficient queries. `segment_raw` redundant with existing `segment`. Fixed alongside #53. |
| 56 | `evhash` is null on all 47 GuidanceUpdate nodes | Medium | **Closed (audit error)** | Correct property name is `evhash16` per spec §1/§3. DB has `evhash16` on 47/47 nodes. Audit queried wrong name `evhash`. |
| 57 | All numeric fields (`value_low`, `value_high`, `value_point`) null on all 47 GuidanceUpdate nodes | HIGH | **Closed (audit error)** | Correct names are `low`/`mid`/`high` per spec §2 fields 7-9. DB has them on 30/47 nodes (17 qualitative-only items correctly null). Audit queried wrong names `value_low`/`value_high`/`value_point`. |
| 58 | `basis_raw` null on 5 OINE items | Low | **Closed (not-a-bug)** | Agent correctly routed "excluding any potential impact from the mark-to-market of minority investments" to `conditions` (per §2 Field #18) and correctly left `basis_norm=unknown` (§6 "excluding special items" didn't match). This is forecast scoping, not an accounting basis declaration — Apple is defining what the forecast covers ("we can't predict mark-to-market volatility"), not declaring a non-GAAP figure. No GAAP OINE figure is provided alongside. Real non-GAAP cases use explicit terms ("non-GAAP", "adjusted") which §6 already catches. Earlier fix (disambiguation rule + broadened §6 trigger) reverted — it conflated forecast scope with accounting basis. Data is correctly captured in `conditions`; nothing is lost. |
| 59 | `canonical_low/mid/high` may be null when `_ensure_ids()` early-returns | Low | **Closed (fail-safe)** | Original description wrong about failure mode. If agent pre-computes `guidance_update_id` without other computed fields, `_build_params()` crashes with KeyError on `guidance_id` (line 238) before reaching DB write — no silent null overwrite is possible. The early-return path has never been triggered: all 48 items across 10 JSON files have `guidance_update_id` unset (agent always lets CLI compute). Latent but fail-safe — worst case is an unhelpful KeyError message, not data corruption. |
| 60 | No Neo4j indexes on denormalized `label_slug` / `segment_slug` properties | Low | **Fixed** | Added 2 indexes to `create_guidance_constraints()`: `CREATE INDEX gu_label_slug IF NOT EXISTS FOR (gu:GuidanceUpdate) ON (gu.label_slug)` and `CREATE INDEX gu_segment_slug IF NOT EXISTS FOR (gu:GuidanceUpdate) ON (gu.segment_slug)`. Auto-created on every write batch via #44 auto-run. |

### Clarification Pack for K8s Open Items (#37-#43)

These items are infra-portability work only. They do **not** change the core guidance design decisions:
- Keep writes off MCP. Agents must not get `write_neo4j_cypher`.
- Keep deterministic write path: JSON payload -> `guidance_write.sh` -> `guidance_write_cli.py` -> `guidance_writer.py` -> Neo4j (Bolt).
- Keep two-layer write gate (`MODE` + `ENABLE_GUIDANCE_WRITES`).

| # | Why this item exists | Must stay unchanged | Required infra change | Done when |
|---|---|---|---|---|
| 37 | `guidance_write.sh` default points to `bolt://localhost:30687`; inside pods, localhost is the pod itself, so write path fails. | Do **not** switch to MCP writes. Keep direct Bolt writer pipeline. | Make writer URI env-driven from one shared config source used by both MCP-read path and CLI-write path; avoid hardcoded localhost assumptions in K8s. | A pod can run both phases end-to-end with same Neo4j target and no connection-refused errors. |
| 38 | `guidance-qa-enrich` example hardcodes `--write`, which can force DB dependency during dry runs. | Keep existing phase semantics and writer path. | Make invocation mode-aware: `dry_run/shadow -> --dry-run`, `write -> --write` in docs/prompts/scripts. | Running dry_run does not require live write-path DB connectivity; write mode still persists correctly. |
| 39 | Guidance jobs rely on Bash behavior (`source`, wrapper scripts); missing Bash/SHELL caused runtime failures. | Keep shell-wrapper approach (`guidance_write.sh`) and current script interface. | Document and enforce runtime contract: image must include `/bin/bash`; set `SHELL=/bin/bash` in job env. | Fresh pod runs both phases without shell/runtime errors. |
| 40 | Claude CLI blocks `--dangerously-skip-permissions` under root; root execution fails before guidance logic runs. | Keep non-interactive Claude invocation pattern and safety controls. | Enforce pod security context: `runAsNonRoot: true`, `runAsUser: 1000`, `runAsGroup: 1000` (or equivalent non-root UID/GID). | Job starts and executes Claude flows without root-permission rejection. |
| 41 | MCP tool availability drift observed without strict config loading; agents can lose required tools at runtime. | Keep tool boundaries (no MCP write tool in guidance agents). | Standardize `--strict-mcp-config` for guidance runs and validate required tools at startup. | Multiple consecutive runs expose identical required tool set and avoid missing-tool failures. |
| 42 | GHCR pull failures (`403`) make runtime startup non-deterministic. | Keep guidance code path and agent/skill behavior unchanged. | Commit to one supported image strategy (GHCR with pull secret, or vetted fallback image) and pin version/digest with documented fallback. | Cold-start in cluster is repeatable; image pull succeeds without manual intervention. |
| 43 | No deterministic pre-prod gate currently proves full two-phase behavior after infra changes. | Keep two-phase flow and no-MCP-write architecture. | Use a mode-aware canary contract: either run isolated `MODE=write` end-to-end with cleanup, or pre-seed Phase 1 rows then run `MODE=dry_run`. Do not require "P2 success" from `MODE=dry_run` when 7E has no Phase 1 rows. | Canary criteria are explicit, reproducible, and aligned with phase dependencies. |

**Additional prerequisite for #37-#43 (must be explicit in K8s runbooks):** mount the repo at exact path `/home/faisal/EventMarketDB` unless you patch path assumptions. Current guidance runtime depends on absolute paths in `.claude/settings.json` hooks and in `guidance_write_cli.py` (`sys.path.insert`).

**Recommended execution order**: 42 -> 40 -> 39 -> 41 -> 37 -> 38 -> 43
Rationale: first make runtime boot reliable and compliant, then align connectivity and mode behavior, then lock with canary.

### Clarification Pack for K8s Deep-Trace Items (#47-#51)

Found via full pipeline trace (2026-02-28). These supplement #37-#43 — same principle: infra-portability only, no core guidance design changes.

| # | Why this item exists | Must stay unchanged | Required infra change | Done when |
|---|---|---|---|---|
| 47 | `guidance_write.sh:14-16` force-sets credentials with plaintext password as defaults. #37 covers URI only — credentials are separate env vars. | Keep `guidance_write.sh` wrapper and `${GUIDANCE_..:-default}` override pattern. | Inject `GUIDANCE_NEO4J_USERNAME`, `GUIDANCE_NEO4J_PASSWORD`, `GUIDANCE_NEO4J_DATABASE` from K8s Secret into pod env. Consider removing plaintext defaults from script. | Pod writes authenticate via Secret-sourced credentials, not hardcoded defaults. |
| 48 | Write mode imports `neograph.Neo4jConnection` → `Neo4jManager` → `XBRL`, `config`, `pandas`, `tenacity`, `neo4j`. Missing any of these = `ImportError` at write time. Dry-run is unaffected. | Keep `guidance_writer.py` → `Neo4jManager` connection path. | Ensure container Python version matches venv, or install deps into container-native env. Pin Python version in Dockerfile. | `--write` mode completes without import errors in container. |
| 49 | Agents declare `mcp__neo4j-cypher__read_neo4j_cypher` — the `neo4j-cypher` segment is the MCP server name. Wrong name = tool not found on every read query. | Keep agent tool declarations as-is. | K8s MCP ConfigMap must use `"neo4j-cypher"` as server key, matching `local-cypher-server.sh` naming and agent tool references. This is already documented in `ClaudeCodeonKubernetes.md`; keep it as an explicit enforcement gate here. | Agents can execute QUERIES.md queries (1A, 1B, 2A, 2B, 3B, etc.) from inside pod. |
| 50 | `guidance_write_cli.py:60-61` uses absolute `/home/faisal/EventMarketDB` path for `sys.path.insert`. Breaks if mount path differs. | Keep CLI entry point and import structure. | Either (a) mount repo at exact path, or (b) patch CLI to use `os.path.dirname(os.path.abspath(__file__))` for relative resolution. | CLI runs successfully regardless of where repo is mounted. |
| 51 | `CLAUDE_PROJECT_DIR` improves consistency across the full project toolchain; guidance-only path may still work without it when cwd/path assumptions are satisfied. | Keep project-scoped skills/agents/hooks layout. | Set `CLAUDE_PROJECT_DIR=/home/faisal/EventMarketDB` in pod env (or match mount path) as a recommended baseline, especially for agents/hooks/scripts that reference `$CLAUDE_PROJECT_DIR`. | `claude -p` in container resolves guidance skill/agents reliably and broader project hooks/scripts behave consistently. |

**Recommended execution order for #47-#51**: 48 -> 47 -> 49 -> 50 -> 51
Rationale: fix Python deps first (write path won't work without them), then credentials, then MCP naming, then path fragility and project dir.

---

## Run 7 — Full 6-Transcript Re-extraction (2026-02-27, MODE=write)

**Session**: 02:11:36 – 03:00:10 UTC (48m 34s total wall clock)
**Mode**: write (all items persisted to Neo4j)
**Orchestrator**: main conversation invoking `/guidance-extractor` skill per transcript

| # | Transcript ID | FY/Q | P1 Items | P1 Time | P2 Enriched | P2 New | P2 Time | Total Time | P1 Tokens | P2 Tokens | Issues |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | AAPL_2023-11-03T17.00.00-04.00 | FY2023 Q4 | 10 | 3m27s (207s) | 4 | 0 | 3m10s (190s) | 6m37s | 94k (21 calls) | 94k (16 calls) | Minor: P2 enriched 4 vs prior 5 |
| 2 | AAPL_2024-10-31T17.00.00-04.00 | FY2024 Q4 | 6 | 2m51s (171s) | 1 | 0 | 2m49s (169s) | 5m40s | 91k (21 calls) | 89k (16 calls) | P2 enriched 1 vs prior 2 |
| 3 | AAPL_2025-01-30T17.00.00-05.00 | FY2025 Q1 | 6 | 2m33s (153s) | 1 | 0 | 2m12s (132s) | 4m45s | 80k (17 calls) | 86k (15 calls) | Matches prior run exactly |
| 4 | AAPL_2025-05-01T17.00.00-04.00 | FY2025 Q2 | 5 | 8m01s (481s) | 2 | 0 | 3m07s (187s) | 11m08s | 111k (41 calls) | 90k (16 calls) | **ISSUES**: #32 tariff standalone, #33 capital alloc items, #34 slow |
| 5 | AAPL_2025-07-31T17.00.00-04.00 | FY2025 Q3 | 8 | 3m16s (196s) | 3 | 2 (CapEx, US Invest) | 3m46s (226s) | 7m02s | 85k (24 calls) | 95k (18 calls) | #32 tariff again, #33 DPS again, CapEx Q&A good |
| 6 | AAPL_2025_3 | FY2025 Q3 (dup?) | 8 | 3m12s (192s) | 4 | 2 (CapEx, US Invest) | 4m26s (266s) | 7m38s | 84k (20 calls) | 100k (21 calls) | Duplicate of #5 — Issue #35. Same items. |

### Run 7 Issue Check — Transcript #1

| Prior Issue | Check | Result |
|---|---|---|
| #1 raw Cypher bypass | Can't see internal tool calls from orchestrator | Assumed OK (write_neo4j_cypher removed from tools) |
| #5 WHA member | 5/5 member links including WHA→WearablesHomeandAccessoriesMember | CONFIRMED FIXED |
| #7 Q&A synthesis | 4/10 enriched (vs prior 5/10) | OK — minor delta |
| #20 unit double-scaling | OpEx 14,400-14,600 m_usd correct | OK |
| #26 segment decomposition | Revenue segments: label=Revenue, segment=iPhone/Mac/etc | CONFIRMED FIXED |
| #28 PER_SHARE_LABELS | No EPS items in this transcript | N/A |
| #30 batch summary undercount | All items new (was_created=true) | N/A (first run) |
| #31 derivation default | All 10 items have explicit derivation values | OK |

**Observation**: P2 enriched 4 items vs prior run's 5. Missing enrichment might be Gross Margin (previously enriched from 3 Q&A exchanges). Not a regression — agent judgment call on borderline cases. Will monitor across remaining transcripts.

### Run 7 Post-Mortem

**Totals across all 6 transcripts:**

| Metric | Value |
|---|---|
| Wall clock time | 48m 34s |
| Total P1 items extracted | 43 (across 6 transcripts) |
| Total P2 enriched | 15 |
| Total P2 new Q&A-only | 4 |
| Grand total items in Neo4j | 47 (43 P1 + 4 new) |
| Total tokens | ~1.1M |
| Total tool calls | ~246 |
| Errors | 0 |

**Timing per transcript:**

| # | Transcript | P1 Time | P2 Time | Total | Tokens |
|---|---|---|---|---|---|
| 1 | FY2023 Q4 | 3m27s | 3m10s | 6m37s | 188k |
| 2 | FY2024 Q4 | 2m51s | 2m49s | 5m40s | 180k |
| 3 | FY2025 Q1 | 2m33s | 2m12s | 4m45s | 166k |
| 4 | FY2025 Q2 | 8m01s | 3m07s | 11m08s | 201k |
| 5 | FY2025 Q3 | 3m16s | 3m46s | 7m02s | 180k |
| 6 | AAPL_2025_3 (dup) | 3m12s | 4m26s | 7m38s | 183k |
| **Avg (excl #4 outlier)** | **3m04s** | **3m17s** | **6m20s** | **179k** |

**Unit audit — all correct:**
- `percent` for Gross Margin and Tax Rate
- `m_usd` for OpEx, OINE, Tariff Cost Impact, Share Repurchase, US Investment
- `usd` for DPS (per-share — Issue #28 PER_SHARE_LABELS fix working for DPS)
- `percent_yoy` for qualitative Revenue guidance
- No double-scaling (Issue #20 fix held)

**New issues found (4):**

| # | Issue | Severity | Transcripts affected |
|---|---|---|---|
| 32 | Tariff Cost Impact as standalone (§13 regression) | Medium | #4, #5, #6 |
| 33 | Capital allocation items (DPS, Repurchase, Investment) as guidance | Low | #4, #5, #6 |
| 34 | Transcript #4 2-3x slower (truncated PR recovery) | Low | #4 only |
| 35 | Duplicate source IDs create duplicate nodes | Medium | #5 + #6 |

**What held from prior runs:**
- Issue #1 (raw Cypher bypass): No regression — agents used CLI write path
- Issue #5 (WHA member): All member links correct
- Issue #7 (Q&A synthesis): Working — P2 enriches and creates new items
- Issue #10 (FX standalone): FX correctly in conditions
- Issue #20 (unit scaling): No double-scaling
- Issue #26 (segment decomposition): Correctly splitting label+segment

**What regressed:**
- Issue #21 → #32: Tariff Cost Impact as standalone came back. The §13 "factors are conditions" rule is not strong enough when the factor is a quantified dollar amount ($900M, $1.1B). Agent sees a number and extracts it.

**Key recommendation**: Issues #32 and #33 need prompt-level fixes. #32 needs a stronger rule ("quantified factors like tariff costs, FX headwinds, or week-count impacts go in conditions even when dollar amounts are given"). #33 needs a new quality filter ("capital allocation announcements — dividends, buybacks, investment pledges — are not operational guidance"). #35 needs upstream dedup.

---

## All AAPL Transcript Runs — Two-Invocation Pipeline (Runs 1-6)

### Summary

| # | Transcript | Period | P1 Items | P2 Enriched | P2 New | Total Items | P1 Time | P2 Time | Total Time |
|---|---|---|---|---|---|---|---|---|---|
| 1 | AAPL_2023-11-03 | Q1 FY2024 | 10 | 5 (50%) | 0 | 10 | 4m42s | 5m01s | 9m43s |
| 2 | AAPL_2024-10-31 | Q1 FY2025 | 6 | 2 (33%) | 0 | 6 | 3m44s | 3m26s | 7m10s |
| 3 | AAPL_2025-01-30 | Q2 FY2025 | 6 | 1 (17%) | 0 | 6 | 3m31s | 2m32s | 6m03s |
| 4 | AAPL_2025-05-01 | Q3 FY2025 | 1 | 0 (0%) | 0 | 1 | 4m19s | 1m50s | 6m09s |
| 5 | AAPL_2025-07-31 | Q4 FY2025 | 6 | 3 (50%) | 1 | 7 | 3m06s | 3m31s | 6m37s |
| **Total** | | | **29** | **11 (38%)** | **1** | **30** | **19m22s** | **16m20s** | **~35m42s** |

### Token Usage

| # | P1 Tokens | P2 Tokens | Total Tokens | P1 Tool Calls | P2 Tool Calls |
|---|---|---|---|---|---|
| 1 | 98k | 104k | 202k | 31 | 40 |
| 2 | 91k | 91k | 182k | — | — |
| 3 | 89k | 81k | 170k | — | — |
| 4 | — | — | — | — | — |
| 5 | 82k | 91k | 173k | 22 | 23 |

### Graph Verification (Neo4j)

| # | Items in Graph | Q&A Enriched | PR-Only | Q&A-Only New | UPDATES | FROM_SOURCE | FOR_COMPANY | HAS_PERIOD | MAPS_TO_CONCEPT | MAPS_TO_MEMBER |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 10 | 5 | 5 | 0 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 5/10 |
| 2 | 6 | 2 | 4 | 0 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 1/6 |
| 3 | 6 | 1 | 5 | 0 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 0/6 |
| 4 | 1 | 0 | 1 | 0 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 |
| 5 | 7 | 3 | 3 | 1 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 0/7 |
| **Total** | **30** | **11** | **18** | **1** | **30/30** | **30/30** | **30/30** | **30/30** | **30/30** | **6/30** |

All 5 core edges (UPDATES, FROM_SOURCE, FOR_COMPANY, HAS_PERIOD, MAPS_TO_CONCEPT) at 100%. MAPS_TO_MEMBER only applies to segment-level items (Run 1 had 5 segment Revenue items; Run 2 had 1 Services; Runs 3-5 had no segment breakdowns).

### Per-Run Notes

**Run 1 (Q1 FY2024)** — Richest transcript. 5 segment Revenue items (iPhone, Mac, iPad, WH&A, Services) + 5 Total items. Phase 2 enriched Revenue, iPhone Revenue, Mac Revenue, Services Revenue, Gross Margin from 23 Q&A exchanges. Feature flag resolved via sed-i (pre-fix). Stale /tmp file collision (Issue #14).

**Run 2 (Q1 FY2025)** — Apple dropped per-segment guidance. 6 Total-level items only. Phase 2 enriched Revenue and Gross Margin from Q&A. Existing guidance labels reused from Run 1 (no new Guidance parent nodes created). Feature flag resolved via Python module override.

**Run 3 (Q2 FY2025)** — Kevan Parekh as new CFO. Phase 2 found 1 Gross Margin enrichment from 3 Q&A exchanges. **Phase 2 write BLOCKED** — agent gave up on feature flag (Issue #17 — data loss). Manually written via CLI. Feature flag fix applied after this run.

**Run 4 (Q3 FY2025)** — Outlier: only 1 item (Revenue). **Truncated PreparedRemarks** — CFO section cut at 6,782 chars before specific guidance numbers (Issue #18). Agent recovered Revenue guidance from Q&A exchange #10 and cross-referenced 8-K press release. Tariff $900M correctly classified as condition (Issue #10 quality filter). Phase 2: 0 enrichments (genuinely sparse tariff-dominated call). Feature flag env var fix worked — much faster resolution.

**Run 5 (Q4 FY2025)** — Cleanest run. 6 PR items + 1 new CapEx from Q&A ("grow substantially, not exponentially", AI-driven, medium-term). Phase 2 enriched Revenue (tariff pull-ahead ~1pt, iPad comp), Gross Margin (tariff cost dynamics QoQ), Services Revenue (Google court ruling as key assumption). 20 Q&A exchanges analyzed. Feature flag resolved instantly via env var. Phase 2 did readback verification (unlike earlier runs).

### Cross-Run Observations

- **Q&A enrichment rate**: 38% overall (11/29 PR items enriched) + 1 new Q&A-only item
- **Run 4 was the outlier** — upstream data quality (truncated PR), not extraction quality
- **Feature flag evolution**: sed-i (Run 1) → Python override (Run 2) → gave up / data loss (Run 3) → env var fix (Runs 4-5, instant resolution)
- **Two-invocation pipeline validated**: Phase 2 always processes Q&A (structural guarantee). Never skipped.
- **Apple guidance density declining**: FY2024 had per-segment breakdowns; FY2025 quarters are Total-level only
- **CapEx first appeared as Q&A-only item in Run 5** — demonstrates Phase 2's value beyond enrichment

### Historical Development Stats

Prior to the two-invocation pipeline, the same first transcript (AAPL_2023-11-03) was run multiple times to debug the extraction system:

| Attempt | Approach | Items | Q&A Enriched | Time | Tokens | Key Issue |
|---|---|---|---|---|---|---|
| Dev Run 1 | Single-pass, raw Cypher | 10 | 0 (0%) | 8m41s | 127k | Bypassed CLI (#1) |
| Dev Run 2 | Single-pass, CLI write | 11 | 0 (0%) | 5m12s | 107k | FX as standalone (#10) |
| Dev Run 3 | Single-agent 3a/3b/3c | 10 | 3 (30%) | ~6m | ~110k | Collapsed phases (#7) |
| Prod Run 1 | Two-invocation | 10 | 5 (50%) | 9m43s | 202k | Feature flag (#12/#13) |

---

## What went RIGHT (All 5 Production Runs)

**Consistent across all runs:**
- Both agents auto-loaded all 3 reference files in parallel
- Phase 1: PR-only compliance — never leaked Q&A content
- Phase 1: All XBRL concepts resolved, member matches where applicable
- Phase 2: Full Q&A Analysis Log with per-exchange verdicts (ENRICHES/NEW/NO GUIDANCE)
- Phase 2: Only wrote changed/new items — never re-wrote untouched PR items
- Phase 2: No fields nulled on enriched items — all Phase 1 values preserved via MERGE+SET
- Phase 2: Quote format consistently `[PR] ... [Q&A] ...` with section citing exact Q&A exchange numbers
- All 5 core edges at 100% (UPDATES, FROM_SOURCE, FOR_COMPANY, HAS_PERIOD, MAPS_TO_CONCEPT)
- FX Impact correctly excluded in all runs (Issue #10 fix held)
- Tariff classification was correct in earlier runs but regressed in Run 7 (Issue #32)

**Standout moments:**
- Run 1: Multi-exchange aggregation (Gross Margin enriched from 3 separate Q&A exchanges)
- Run 4: Agent resourcefully recovered guidance from Q&A + 8-K press release when PR was truncated
- Run 5: Discovered CapEx as new Q&A-only item (medium-term, AI-driven) — first non-PR item across all runs
- Run 5: Cleanest run — env var fix instant, readback verification done, zero wasted turns

---

## Issue Details

### ISSUE 1 (CRITICAL): Agent bypassed the CLI write path

The agent constructed raw Cypher MERGE queries and wrote via `mcp__neo4j-cypher__write_neo4j_cypher` — directly violating Step 5's instruction: "Do NOT construct Cypher manually." It should have used Write tool (JSON) + Bash (`guidance_write.sh`).

**Impact:** The CLI's ID computation, validation, feature flag enforcement, and batch atomicity were all bypassed. Issues #2, #3, #4, and #9 are all direct consequences — fixing #1 auto-fixes all of them.

**Root cause:** The agent has the old Cypher template pattern in its training context. Even though guidance-extract.md now says "use CLI", the agent still has `mcp__neo4j-cypher__write_neo4j_cypher` in its tools and defaulted to raw Cypher construction. The Step 5 instruction ("Do NOT construct Cypher manually") was not strong enough to override the agent's learned behavior.

**Historical alternative that was considered (superseded by final fix):**
1. Keep MCP write only for exceptional operations (DELETE/DDL/recovery).
2. Rely on stronger prompt language to prevent routine write bypass.
3. This option was not selected for guidance agents due to repeated bypass behavior.

**Fix applied (Option A — remove the tool entirely):**
- Removed `mcp__neo4j-cypher__write_neo4j_cypher` from `guidance-extract.md` tools list
- Removed `mcp__neo4j-cypher__write_neo4j_cypher` from `SKILL.md` allowed-tools
- Added top-level WRITE PROHIBITION banner in agent prompt (survives context compaction)
- Strengthened Step 5: "You do NOT have `mcp__neo4j-cypher__write_neo4j_cypher`" + batch instruction
- Verified: SKILL.md, QUERIES.md, PROFILE_TRANSCRIPT.md have zero Cypher write templates — agent invented the MERGE from training knowledge
- **Pending:** Delete Run 2 data, rerun with fixed prompt to verify

### ISSUE 2 (CRITICAL): Wrong MERGE pattern on GuidanceUpdate

Agent used `ON CREATE SET` for ALL properties. Correct pattern: `ON CREATE SET gu.created = $created_ts` + `SET` for everything else. Re-runs won't update properties. **Auto-fixed by #1** — CLI uses correct MERGE pattern from `guidance_writer.py`.

### ISSUE 3 (CRITICAL): 20 MCP write calls instead of 2

CLI batch: 1 Write (JSON) + 1 Bash = 2 tool calls, ~2k tokens.
Actual: 20 MCP writes, ~16k tokens wasted. **Auto-fixed by #1.**

### ISSUE 4 (Medium): Feature flag bypassed

Agent never went through `guidance_writer.py`, so `ENABLE_GUIDANCE_WRITES` was never checked. Global kill switch dead. **Auto-fixed by #1.**

### ISSUE 5 (Medium): Missing WHA MAPS_TO_MEMBER edge

WHA item has no `MAPS_TO_MEMBER` edge. Previous run (Run 1) correctly linked to `WHAMember`. Agent likely didn't resolve the member match this time. Need to check if WHAMember exists in member cache results.

### ISSUE 6 (Medium): Segment Revenue items missing MAPS_TO_CONCEPT

5 of 6 Revenue segment items have `xbrl_concept: null` and no MAPS_TO_CONCEPT edge. Only Revenue(Total) got `RevenueFromContractWithCustomerExcludingAssessedTax`. Per §11, segment items use the segment Member's concept if available. These items DID get member edges (iPhone, Mac, iPad, Services) but not concept edges.

### ISSUE 7 (Medium → Fixed): No Q&A synthesis

All 11 items have `section: "CFO Prepared Remarks"` and quotes prefixed with `[PR]`. Agent read all Q&A exchanges in Step 2 but didn't synthesize any Q&A enrichments. Root cause: cognitive satisficing — PR has clean, explicit guidance; Q&A is conversational and noisy. The aspirational "synthesize richest combined version" rule in PROFILE_TRANSCRIPT.md was not structurally enforced.

**Fix attempt 1** (single-agent 3a/3b/3c — `qa-synthesis-fix.md`):
- Split Step 3 into two-phase extraction: 3a (PR only), 3b (Q&A enrichment), 3c (merged items)
- Run 3 result: 3/10 enriched. Agent collapsed 3a/3b into one thinking pass — no tool call boundary to enforce separation. Insufficient.

**Fix attempt 2** (two-invocation — `two-invocation-qa-fix.md`):
- Separate agents: `guidance-extract` (PR-only) → `guidance-qa-enrich` (Q&A enrichment)
- Physical invocation boundary makes it impossible to skip Q&A — Phase 2's entire purpose is Q&A
- Created `guidance-qa-enrich.md` agent, Query 7E for readback, `guidance-extractor.md` orchestrator skill
- Run 4 result: **5/10 items enriched** from Q&A (up from 0/11 Run 2, 3/10 Run 3)
- Full Q&A Analysis Log produced: 23 exchanges analyzed (5 enriched, 0 new, 18 no_guidance)
- **Verified working.** FX Impact correctly excluded (10 items, not 11).

### ISSUE 8 (Low → Closed): iPad/WHA share evhash

Both share `f611c8fee63e3f44`. Qualitative text identical ("decelerate significantly from Sept quarter"), both have null numerics. Quotes differ but evhash doesn't include quote field. Conditions also very similar. **By design** — evhash fingerprints the value signal, and these two items genuinely carry the same directional guidance. They remain separate nodes because the slot-based ID includes segment (`revenue:ipad` vs `revenue:wha`).

### ISSUE 9 (CRITICAL): Peak context 81% — compaction risk

105k/130k tokens used. For larger transcripts (MSFT 30+ Q&A, AMZN multi-segment), this would trigger compaction mid-extraction — exactly RC-1 from Run 1. **Auto-fixed by #1** — CLI path saves ~14k tokens, bringing peak to ~58%.

### ISSUE 10 (Low → Fixed): FX Impact extracted as standalone item

Agent created a standalone `FX Impact` guidance item (-1.0 percent_points) when the CFO's statement ("we expect a negative year-over-year revenue impact of about one percentage point") was a condition on Revenue, not an independent metric. The same information was already in Revenue(Total)'s conditions field (`-1pp FX`), creating redundancy. Previous run correctly folded FX into conditions only.

**Fix applied:** Added quality filter to SKILL.md §13: "If a forward-looking statement quantifies a factor affecting another guided metric (e.g., FX headwind, week count, commodity cost tailwind), capture it in that metric's `conditions` field — not as a standalone item."

### ISSUE 11 (Low): 3B query result too large for direct tool result

Large transcripts overflow MCP tool result size limit. Agent falls back to persisting output to file and parsing via Bash+Python (3-4 extra tool calls). Minor inefficiency, unavoidable with large transcripts. Potential fix: split 3B into separate PR and Q&A queries, or paginate.

### ISSUE 12 (Medium → Fixed): Agent modified `config/feature_flags.py` directly with `sed -i`

Agent used `sed -i` to flip `ENABLE_GUIDANCE_WRITES = False` → `True` in source code. Persistent, globally visible, bypasses any version control. **Fixed:** Added env var override to `guidance_writer.py` (lines 26-35). Agents now use `ENABLE_GUIDANCE_WRITES=true bash guidance_write.sh --write` — process-scoped, no config file editing.

### ISSUE 13 (Low → Fixed): Phase 2 re-discovers feature flag toggle

Phase 2 agent spent ~60s and 8 extra tool calls rediscovering how to enable writes (reading config files, checking feature flags). **Auto-fixed by #12** — env var in the Bash command, no discovery needed.

### ISSUE 14 (Low): Stale /tmp JSON file collision

Phase 1 wrote to `/tmp/gu_AAPL_*.json` but a stale file from a prior run already existed. Agent detected it, deleted, and rewrote (+15s overhead). Fix: use unique filenames with timestamp or PID, or always overwrite without checking. **Observed in Run 6**: agent wrote JSON up to 5 times during the Issue #20 self-correction cycle for the same source.

### ISSUE 15 (Low → Won't-fix): Phase 2 skipped readback verification

CLI already returns structured JSON with `was_created`, edge linking results, and errors — agent parses this directly. A post-write readback query is redundant (verifying the verifier). Phase 1's readback was agent improvisation, not a prompted step. No observed failure mode where CLI exit 0 was wrong across all runs.

### ISSUE 16 (Low → Fixed): Guidance periods share `:Period` label with XBRL periods

Both used `:Period` but with completely disjoint schemas. **Fixed by GuidancePeriod redesign** (`guidance-period-redesign.md`). New `:GuidancePeriod` label with calendar-based `gp_` IDs, company-agnostic. Old `guidance_period_` `:Period` nodes deleted (31 GuidanceUpdate + 7 Period nodes). Run 6 confirmed all items use new format. Issues #24/#25 now fixed — all 3 constraints + 4 sentinels verified.

### ISSUE 17 (CRITICAL → Fixed): Phase 2 feature flag data loss

Phase 2 computed Q&A enrichment but could not persist it — agent gave up on the feature flag after trying multiple workarounds. **DATA LOSS** on Run 3 (Q2 FY2025 Gross Margin enrichment). Evolution across runs: sed-i (Run 1) → Python module override (Run 2) → gave up (Run 3, data loss) → env var fix (Runs 4-5, instant). Fixed: env var check in `guidance_writer.py`, both agent prompts updated.

### ISSUE 18 (Medium): Truncated PreparedRemarks node

Observed on AAPL_2025-05-01T17.00.00-04.00 (Q3 FY2025). CFO Kevin Parekh's prepared remarks end mid-sentence at 6,782 characters — right before the specific guidance numbers for Gross Margin, OpEx, OINE, and Tax Rate. The text cuts off after "color at the total company level."

**Impact across runs:**
- **Original Run 4**: Only 1 item extracted (Revenue from Q&A recovery). Tariff $900M classified as condition.
- **Run 6 (current)**: 2 items extracted (Revenue + Tariff Cost Impact as standalone — see Issue #21). Gross Margin, OpEx, OINE, Tax Rate, Services Revenue all lost.
- Q&A Exchange #10 references "June quarter guide of low to mid single-digit revenue growth" — confirming guidance was given verbally but is missing from the stored PreparedRemark node.
- 8-K press release checked — contains actuals only, no forward guidance.
- Services Revenue: CFO explicitly declined ("we aren't providing the category level of color today, given the uncertainty").

**Root cause:** Upstream data quality issue in the Transcript node, not an extraction bug. The PreparedRemark node's `content` field was truncated at ingestion time.

**Scope:** Unknown how many transcripts are affected. Only observed on this one AAPL transcript across 5 sources. Fix: audit PreparedRemarks nodes for truncation (check if last sentence ends mid-word or without punctuation mark).

**Agent recovery:** Resourceful — cross-referenced Q&A exchanges + 8-K press release. Recovered Revenue guidance from analyst questions. Could not recover Gross Margin/OpEx/OINE/Tax Rate because analysts did not repeat the specific numbers in Q&A.

---

## Extraction Results — All 5 Runs (Two-Invocation Pipeline)

### Run 1: AAPL_2023-11-03 — Q1 FY2024 (10 items, 5 enriched)

| # | Metric | Segment | Enriched? | Section | Low | High | Unit |
|---|---|---|---|---|---|---|---|
| 1 | Revenue | Total | **Yes** | CFO PR + Q&A #4 | -- | -- | m_usd |
| 2 | Revenue | iPhone | **Yes** | CFO PR + Q&A #4, #19 | -- | -- | m_usd |
| 3 | Revenue | Mac | **Yes** | CFO PR + Q&A #1 | -- | -- | m_usd |
| 4 | Revenue | iPad | -- | CFO PR | -- | -- | m_usd |
| 5 | Revenue | WH&A | -- | CFO PR | -- | -- | m_usd |
| 6 | Revenue | Services | **Yes** | CFO PR + Q&A #9 | -- | -- | m_usd |
| 7 | Gross Margin | Total | **Yes** | CFO PR + Q&A #3, #7, #16 | 45.0 | 46.0 | percent |
| 8 | OpEx | Total | -- | CFO PR | 14,400 | 14,600 | m_usd |
| 9 | OINE | Total | -- | CFO PR | -200 | -200 | m_usd |
| 10 | Tax Rate | Total | -- | CFO PR | 16.0 | 16.0 | percent |

### Run 2: AAPL_2024-10-31 — Q1 FY2025 (6 items, 2 enriched)

| # | Metric | Segment | Enriched? | Section | Low | High | Unit |
|---|---|---|---|---|---|---|---|
| 1 | Revenue | Total | **Yes** | CFO PR + Q&A | -- | -- | percent_yoy |
| 2 | Services Revenue | Total | -- | CFO PR | -- | -- | percent_yoy |
| 3 | Gross Margin | Total | **Yes** | CFO PR + Q&A | 46.5 | 47.5 | percent |
| 4 | OpEx | Total | -- | CFO PR | 15,300 | 15,500 | m_usd |
| 5 | OINE | Total | -- | CFO PR | -50 | -50 | m_usd |
| 6 | Tax Rate | Total | -- | CFO PR | 16.0 | 16.0 | percent |

No segment breakdowns — Apple dropped per-segment guidance starting FY2025.

### Run 3: AAPL_2025-01-30 — Q2 FY2025 (6 items, 1 enriched)

| # | Metric | Segment | Enriched? | Section | Low | High | Unit |
|---|---|---|---|---|---|---|---|
| 1 | Revenue | Total | -- | CFO PR | -- | -- | percent_yoy |
| 2 | Services Revenue | Total | -- | CFO PR | -- | -- | percent_yoy |
| 3 | Gross Margin | Total | **Yes** | CFO PR + Q&A | 46.5 | 47.5 | percent |
| 4 | OpEx | Total | -- | CFO PR | 15,400 | 15,600 | m_usd |
| 5 | OINE | Total | -- | CFO PR | -50 | -50 | m_usd |
| 6 | Tax Rate | Total | -- | CFO PR | 16.0 | 16.0 | percent |

Phase 2 write was BLOCKED (Issue #17). Gross Margin enrichment manually written via CLI.

### Run 4: AAPL_2025-05-01 — Q3 FY2025 (1 item, 0 enriched)

| # | Metric | Segment | Enriched? | Section | Low | High | Unit |
|---|---|---|---|---|---|---|---|
| 1 | Revenue | Total | -- | CFO PR | -- | -- | percent_yoy |

Outlier: PreparedRemarks truncated (Issue #18). Only Revenue recovered from Q&A cross-reference. Tariff $900M in conditions.

### Run 5: AAPL_2025-07-31 — Q4 FY2025 (7 items, 3 enriched + 1 new)

| # | Metric | Segment | Enriched? | Section | Low | High | Unit |
|---|---|---|---|---|---|---|---|
| 1 | Revenue | Total | **Yes** | CFO PR + Q&A | -- | -- | percent_yoy |
| 2 | Services Revenue | Total | **Yes** | CFO PR + Q&A | -- | -- | percent_yoy |
| 3 | Gross Margin | Total | **Yes** | CFO PR + Q&A | 46.0 | 47.0 | percent |
| 4 | OpEx | Total | -- | CFO PR | 15,600 | 15,800 | m_usd |
| 5 | OINE | Total | -- | CFO PR | -25 | -25 | m_usd |
| 6 | Tax Rate | Total | -- | CFO PR | 17.0 | 17.0 | percent |
| 7 | **CapEx** | Total | **NEW** | Q&A #17 (Aaron Rekers) | -- | -- | m_usd |

First Q&A-only item across all runs. CapEx: "grow substantially, not exponentially" (medium-term, AI-driven).

### ISSUE 19 (Low): `guidance-extractor` skill not in user-invocable registry

`/guidance-extractor AAPL transcript ...` fails — skill not found. The agent falls back to executing the logic manually ("The skill isn't in the user-invocable registry. I'll execute its logic directly").

**Root cause:** Claude Code's skill registry discovers skills at `.claude/skills/{name}/SKILL.md` (subdirectory containing `SKILL.md`). The orchestrator skill is at `.claude/skills/guidance-extractor.md` — a bare `.md` file directly in the skills root. This structure is invisible to the registry.

**Evidence:** Every other registered skill (`earnings-orchestrator`, `guidance-inventory`, `perplexity-ask`, etc.) follows the `{name}/SKILL.md` convention. The system-provided skill list confirms `guidance-extractor` is absent while all subdirectory-based skills are present.

**Fix:** Move `.claude/skills/guidance-extractor.md` → `.claude/skills/guidance-extractor/SKILL.md`. No content changes needed — the file already has valid frontmatter (`description:`) and `$ARGUMENTS` parsing.

### ISSUE 20 (Medium): Unit double-scaling bug — agent pre-scales values AND sets unit_raw to "billion"

Agent writes values already converted to millions (e.g., `low: 15100.0` for "$15.1 billion") but sets `unit_raw: "billion"`. The canonicalizer in `build_guidance_ids()` sees `unit_raw: "billion"` and multiplies by 1000 again → `canonical_low: 15100000.0` (15.1 trillion instead of 15.1 billion).

**Root cause:** The agent is doing mental math (15.1B → 15,100M) before writing the JSON, then also declaring the unit as "billion". The system expects one or the other:
- Pass raw values as spoken (`low: 15.1`, `unit_raw: "billion"`) → canonicalizer converts to m_usd
- Pass pre-converted values (`low: 15100.0`, `unit_raw: "million"`) → canonicalizer recognizes already in millions

**Impact:** All items with billion-scale values (Revenue, OpEx, OINE) would have 1000x inflated canonical values. MERGE+SET means corrected values overwrite on rerun.

**Self-corrected: YES.** Agent detected the bug during post-write readback (saw `15100000.0` instead of `15100.0`), diagnosed the root cause, and restarted the full pipeline with corrected raw values (`15.1` billion → canonicalized to `15100.0` m_usd). MERGE+SET overwrote the bad values. No manual intervention needed. However, self-correction cost ~3 extra minutes and ~43 tool calls (vs typical ~20) due to reloading all 3 reference files and re-running the entire pipeline.

**Observed on:** AAPL_2025-01-30T17.00.00-05.00 (Q2 FY2025), Run 6 Phase 1. Not observed on any other transcript in this batch — other agents passed raw values correctly.

**Fix options:**
1. Prompt fix: instruct agent to always pass raw transcript values and let the system canonicalize
2. Code fix: detect and warn when values seem pre-scaled (e.g., `unit_raw: "billion"` but value > 1000)
3. Both — prompt is primary, code is safety net

### ISSUE 21 (Medium): Tariff Cost Impact extracted as standalone despite quality filter citation — Issue #10 regression

P1-Q3FY2025 agent (AAPL_2025-05-01) extracted `Tariff Cost Impact` as a standalone item ($900M, point derivation) despite explicitly citing the Issue #10 quality filter.

**Agent's reasoning trace (verbatim):**
1. `[10:09:50]` — "the $900M tariff cost is a standalone cost estimate with a specific number"
2. `[10:10:06]` — "Wait — per SKILL.md quality filter: 'Factors are conditions, not items...' The $900M tariff impact is a factor affecting cost of goods sold / gross margin. It should go in the conditions of the revenue guidance (or gross margin if we had it), not as a standalone item. I already included it in the Revenue conditions. Let me not create it as a standalone item."
3. Same message continues: "However, this is also..." — then reversed and kept it as standalone
4. `[10:10:27]` — "Both items are valid" — dry-run with 2 items (Revenue + Tariff)

**Impact:** Previous Run 4 extracted 1 item (Revenue only). Current run: 2 items (Revenue + Tariff Cost Impact). The $900M was correctly in Revenue's `conditions` field AND as a standalone — creating redundancy.

**Root cause:** 100% recall priority ("when in doubt, extract it") overrides quality filter when the agent encounters a specific dollar figure. The agent cited the filter, agreed with it, said "let me not create it", then the recall instinct won in the same thought. The quality filter in SKILL.md §13 is not strong enough to override the extraction maximalism instinct.

**Self-corrected: NO.** Agent kept the standalone item through dry-run, write, and readback verification without flagging it.

**Fix (prompt — unreliable):** Strengthen quality filter language: "If you catch yourself citing this rule and then creating the item anyway, the rule wins. Delete the standalone item." — This is a prompt-level nudge. LLMs cannot guarantee 0% regression on judgment calls; the same model on the same transcript may still reverse itself.

**Fix (code — 0% regression):** Add a validation gate in `guidance_write_cli.py` that rejects items which have NO XBRL concept AND whose label slug is not already in the Guidance graph:

```python
# In guidance_write_cli.py validation loop, before write:
if item.get('xbrl_qname') is None:
    label_slug = slugify(item['label'])  # e.g. "tariff_cost_impact"
    known_labels = get_known_guidance_labels(ticker)  # query: MATCH (g:Guidance) WHERE g.ticker=$ticker RETURN DISTINCT g.label_slug
    if label_slug not in known_labels:
        errors.append(f"REJECTED: '{item['label']}' has no XBRL concept and is not a known guidance metric — likely a factor, not a standalone item")
        continue
```

**Trade-offs:**
- **Reliability:** 100% — code gate cannot be overridden by LLM reasoning
- **False positives:** First-ever extraction of a genuinely new metric with no XBRL concept would be blocked. Mitigated by: (a) most real guidance maps to XBRL, (b) blocked items logged with REJECTED prefix for human review, (c) can add to known-labels allowlist if legitimate
- **Cost:** ~1 extra Cypher query per write batch (cached after first call)

### ISSUE 22 (Medium): P2-Q3FY2025 dropped Revenue enrichment — false "already enriched" claim

P2-Q3FY2025 agent classified Q&A #10 (Amit Daryanani) as `ENRICHES Revenue` but then annotated it as "(already enriched in prior run)" and did NOT write the enrichment. Only 1 item was written (Tariff Cost Impact enriched), not 2.

**What was missed:** Q&A #10 adds: CFO reiterates low-to-mid single digits YoY, **FX slight headwind** (new detail), **declines category-level color** (new condition). These details were NOT in the P1 Revenue item, which only had the basic "low to mid single-digit YoY growth" from Q&A recovery.

**Root cause:** The P1 item was itself recovered from Q&A (not from PR, since PR was truncated — Issue #18). The P2 agent appears to have confused "P1 already used Q&A data to create this item" with "this item was already enriched by a prior P2 run." There was no prior P2 run — this was the first Phase 2 execution for this source. The "(already enriched in prior run)" annotation is factually incorrect.

**Self-corrected: NO.** Agent did not write the Revenue enrichment.

**Impact:** Revenue item for Q3 FY2025 is missing FX headwind condition and category-level decline context. Marginal data loss — the core guidance number ("low to mid single-digit") is correct, only the conditions/context are incomplete.

**Fix (prompt — unreliable):** Add to P2 agent prompt: "When P1 items were recovered from Q&A (due to truncated PR), P2 enrichment should still add NEW details from Q&A exchanges not already captured. 'P1 used Q&A' ≠ 'already enriched by P2'." — Same LLM reliability caveat: the agent may still hallucinate "already enriched" on any given run.

**Fix (code — 0% regression):** Remove the agent's ability to skip enrichments entirely. Structural change to the P2 write path:

1. P2 agent outputs ALL items it identifies as enrichable — both the original P1 fields AND the enriched fields — in the same JSON format. No skip decisions.
2. `guidance_write_cli.py` reads the P2 JSON, diffs each item against the current graph state (MATCH by `guidance_id`), and writes ONLY fields that changed or were added.
3. If the P2 output is identical to what's already in the graph, the CLI writes nothing (no-op). If there are new conditions/quotes/qualitative details, the CLI merges them.

```python
# In guidance_write_cli.py — P2 enrichment diff logic:
for item in p2_items:
    existing = query_existing_update(item['guidance_id'], item['source_id'])
    if existing is None:
        # New item from P2 (e.g., CapEx discovered in Q&A) — write as-is
        write_item(item)
    else:
        diff = compute_field_diff(existing, item)
        if diff:
            merge_fields(item['guidance_id'], diff)  # SET only changed fields
        # else: no-op, already identical
```

**Trade-offs:**
- **Reliability:** 100% — agent cannot drop enrichments because it never decides to skip; all items flow to CLI, CLI does the diff
- **Cost:** P2 JSON payload is larger (includes all items, not just enriched ones). ~1 extra Cypher read per item for diff. Negligible.
- **Risk:** If agent corrupts an existing field (e.g., overwrites a correct `low` value with null), the diff would write the corruption. Mitigated by: (a) diff rejects null-overwrites of non-null fields by default, (b) MERGE+SET is already idempotent — re-running P1 restores originals

### ISSUE 23 (Low): P2-Q3FY2025 Q&A verdict inconsistency between analysis and final report

P2-Q3FY2025 agent changed verdicts between its initial analysis log and the final output:

| Exchange | Initial Analysis | Final Report | Delta |
|----------|-----------------|--------------|-------|
| #4 (Ben Ricey) | `ENRICHES Tariff Cost Impact` | `NO GUIDANCE — asks about post-June tariff trajectory; CEO declines to predict beyond June` | Downgraded |

**Impact:** Low. The final verdict is arguably more accurate — CEO declining to predict beyond June is not actionable enrichment. But the inconsistency suggests the agent is doing two passes (analysis → reporting) and changing its mind between them without flagging the change.

**Self-corrected:** Arguably yes — the final verdict is more conservative and more accurate. But the silent reclassification without acknowledgment is concerning for auditability.

### ISSUE 24 (Medium → Fixed): 2 of 3 guidance uniqueness constraints missing in Neo4j

`create_guidance_constraints()` in `guidance_writer.py` defines 3 constraints (`guidance_id_unique`, `guidance_update_id_unique`, `guidance_period_id_unique`) and pre-creates 4 sentinel nodes. It was never executed against the live database.

**Neo4j audit (2026-02-26):**
- `constraint_guidance_id_unique` (Guidance.id) — existed (created by prior ingestion system)
- `guidance_update_id_unique` (GuidanceUpdate.id) — **MISSING**
- `guidance_period_id_unique` (GuidancePeriod.id) — **MISSING**

**Pre-flight checks (all passed):**
- 0 duplicate IDs on GuidanceUpdate (31 nodes), GuidancePeriod (6 nodes), Guidance
- 0 null IDs on any label
- `IF NOT EXISTS` checks both name AND equivalent schema — Guidance constraint is no-op
- `hasPeriod_key` relationship constraint only applies to XBRL edges (key=null on guidance edges, nulls don't violate uniqueness)
- `execute_cypher_query` uses `session.run()` auto-commit — correct for DDL

**Fix applied (2026-02-26):** Ran all 7 statements via `mcp__neo4j-cypher__write_neo4j_cypher`:
1. Guidance constraint → no-op (equivalent `constraint_guidance_id_unique` existed)
2. GuidanceUpdate constraint → **created** (constraints_added: 1)
3. GuidancePeriod constraint → **created** (constraints_added: 1)

**Verified:** `SHOW CONSTRAINTS` confirms all 3 constraints present.

### ISSUE 25 (Medium → Fixed): 3 of 4 sentinel GuidancePeriod nodes missing

Plan (D2) specifies 4 sentinel nodes pre-created: `gp_ST`, `gp_MT`, `gp_LT`, `gp_UNDEF`. Only `gp_MT` existed — created organically when the CapEx item (Run 5, Q&A-only, medium-term) was written.

**Fix applied (2026-02-26):** Ran 4 MERGE statements via MCP write tool:
- `gp_ST` → **created** (nodes_created: 1)
- `gp_MT` → **matched** (properties_set: 3, values unchanged)
- `gp_LT` → **created** (nodes_created: 1)
- `gp_UNDEF` → **created** (nodes_created: 1)

**Verified:** 9 total GuidancePeriod nodes (5 calendar + 4 sentinels), all with correct properties.

### ISSUE 26 (Medium): Segment-qualified labels produce separate Guidance parent nodes instead of grouping under base metric

Segment Revenue items (iPhone, iPad, Mac, WH&A, Services) each create their own Guidance parent node (`guidance:iphone_revenue`, `guidance:ipad_revenue`, etc.) instead of grouping under `guidance:revenue`. The correct model: Guidance node = metric identity (Revenue), GuidanceUpdate = per-source/period/segment instance with segment field for differentiation.

**Affected:** 5 Guidance nodes (8 GuidanceUpdates) should be consolidated into `guidance:revenue`.

**Root cause (3 layers):**
1. **§4 never activated** — SKILL.md §4 "Metric Decomposition" defines the rule but the agent prompt (`guidance-extract.md`) never references it. Pipeline Steps 1-5 cite §6, §11, §12, §13, §17 — not §4. The rule exists in the reference doc but is never invoked.
2. **No code enforcement** — `build_guidance_ids()` line 494 uses `guidance_id = f"guidance:{label_slug}"` directly. No decomposition, no validation. Trusts whatever label it receives.
3. **Redundant segment in label AND segment field** — agent sets label="iPhone Revenue" AND segment="iPhone". The segment_slug in `guidance_update_id` already provides uniqueness.

**Additional finding:** §7 (Segment Assignment Rules) is also only partially referenced in the pipeline (member matching only, not segment assignment).

**Fix:** See Issue #26 fix section below.

### ISSUE 27 (Low): Services Revenue segment inconsistency — segment="Total" in 1 of 4 items

`gu:AAPL_2024-10-31T17.00.00-04.00:services_revenue:gp_2024-10-01_2024-12-31:unknown:total` has `segment="Total"` while the other 3 Services Revenue items have `segment="Services"`. Agent inconsistently classified the same metric across runs. Run 2 (Q1 FY2025) treated "Services Revenue" as a standalone metric (segment=Total); Runs 1, 3, 5 treated it as a segment of Revenue (segment=Services).

**Impact:** The inconsistent segment_slug produces a different `guidance_update_id` slot. If both forms coexist for the same source/period, they'd create duplicate GuidanceUpdate nodes (one with segment=Total, one with segment=Services). Currently no duplication exists because only one run per source.

**Root cause:** Agent prompt doesn't reference §7 segment assignment rules. Without explicit rules, the agent makes ad-hoc decisions.

**Fix:** Add §7 reference to pipeline Step 3. Code-level fix is impractical — segment classification requires LLM judgment.

---

# Fix Issue #26: Segment-Qualified Labels Produce Separate Guidance Parents

## Context

**Problem**: Guidance parent nodes in Neo4j have segment-qualified IDs like `guidance:iphone_revenue`, `guidance:ipad_revenue`, `guidance:mac_revenue` instead of all pointing to `guidance:revenue`. The Guidance node represents a base financial metric (Revenue) — segment distinction belongs on the GuidanceUpdate node, not the Guidance parent.

**Root cause (3 layers)**:
1. SKILL.md §4 has metric decomposition rules but they were **never referenced** in the agent prompt (`guidance-extract.md`). Zero occurrences of "§4" in the pipeline steps.
2. SKILL.md §7 segment assignment rules also not referenced in the extraction step.
3. Without §4/§7 instructions, the LLM outputs `label="iPhone Revenue"` instead of `label="Revenue"` + `segment="iPhone"`. The code at `guidance_ids.py:494` takes the label as-is: `guidance_id = f"guidance:{label_slug}"` → `guidance:iphone_revenue`.

**Additionally**: §4's current text has a bug — its decomposition rules would incorrectly split "Cost of Revenue" → `label="Revenue"` + `segment="Cost of"` because Rule 1 only checks for canonical suffix without distinguishing accounting modifiers from business dimensions.

**Fix approach**: Prompt-only. Amend §4 text to be unambiguous, add §4/§7 references to agent prompts. Zero code changes — the LLM does semantic decomposition, the existing code produces correct IDs from the corrected labels.

**Requirements**:
- Super minimalistic yet close to 100% reliable
- Safe for 10K+ companies — no hardcoded string manipulation in code
- Zero regression risk to existing working functionality
- No over-engineering
- Non-exhaustive lists must not cause LLM overfitting

---

## Changes (4 files, 7 edits, 0 code changes)

### File 1: `.claude/skills/guidance-inventory/SKILL.md`

#### Edit 1A: Add non-exhaustive banner (after line 13, before §1)

Insert after the `**Thinking**:` line (line 13), before the blank line and `## Table of Contents`:

```
**NON-EXHAUSTIVE LISTS**: Every list in this document (metrics, keywords, concepts, instant labels) is a starting set of common examples — NOT a filter. Extract guidance for ANY metric you find, even if unlisted. Create new labels freely. Set `xbrl_qname=null` when no concept matches.
```

**Why**: Prevents LLM overfitting on canonical examples across all high-risk sections.

#### Edit 1B: Fix line 195 — add non-exhaustive reminder at §4 table

Current (line 195):
```
12 canonical metrics. LLM creates new Guidance nodes for metrics not in this table.
```

New:
```
12 common canonical metrics. These are common examples — create new base metrics freely for any company-specific or industry-specific metric not listed here.
```

#### Edit 1C: Fix line 212 — remove contradictory "Services Revenue" example

Current (line 212):
```
Aliases are stored on the Guidance node in `aliases[]`. Non-exhaustive — company-specific metrics (e.g., "Services Revenue" for AAPL) are created dynamically.
```

New:
```
Aliases are stored on the Guidance node in `aliases[]`. Non-exhaustive — new base metrics not in this table (e.g., "Installed Base", "ARPU") are created as-is when no canonical suffix is found (rule 3 below).
```

**Why**: "Services Revenue" directly contradicts §4 decomposition (it SHOULD decompose to Revenue + Services). Replace with genuinely standalone metrics.

#### Edit 1D: Replace §4 Metric Decomposition rules (lines 214-221)

Current (lines 214-221):
```
### Metric Decomposition

When source text qualifies a base metric with a product, segment, geography, or business-unit name:

1. **Identify base metric** — if any canonical label (or variant) from the table above appears as suffix, that's the base
2. **Everything before the base is qualifier** — set as `segment`, joined with ` | ` if multiple, sorted alphabetically
3. **No canonical suffix found** — entire phrase becomes a new `label` with `segment=Total`
4. **Qualifier without a matching Member node** — still decompose; member matching (§7) handles no-match gracefully
```

New:
```
### Metric Decomposition

When source text qualifies a metric, split into `label` (the base metric) + `segment` (the qualifier):

**Decompose** when the qualifier names a business dimension — a product, geography, business unit, or customer type:
- "iPhone Revenue" → `label="Revenue"`, `segment="iPhone"`
- "North America Operating Income" → `label="Operating Income"`, `segment="North America"`
- "Cloud Services Gross Margin" → `label="Gross Margin"`, `segment="Cloud Services"`

**Do NOT decompose** when the qualifier is an accounting or measurement modifier — it changes *what* is being measured, not *who/where*:
- "Cost of Revenue" → `label="Cost of Revenue"`, `segment="Total"` (different metric than Revenue)
- "Net Revenue" → `label="Net Revenue"`, `segment="Total"` (different measurement than Revenue)
- "Adjusted EBITDA" → `label="Adjusted EBITDA"`, `segment="Total"`
- "Pro Forma EPS" → `label="Pro Forma EPS"`, `segment="Total"`

**No qualifier** — just "Revenue" or "EPS" — set label to the metric as-is, `segment="Total"`.

**Simple test**: Could you have this metric for iPhone AND for Total? If yes, the prefix is a segment — decompose. If the prefix changes the financial definition, keep it whole.

**No-match is OK**: If a qualifier doesn't match any Member node, still decompose. Member matching (§7) handles no-match gracefully.
```

**Why**: Old rules would incorrectly decompose "Cost of Revenue" into Revenue + "Cost of". New rules use a clear semantic test (business dimension vs accounting modifier) that the LLM can apply reliably.

#### Edit 1E: Add non-exhaustive reminder at §11 concept pattern map (after line 462, after the concept table)

Insert after the concept pattern map table (after line 462):

```
This maps the 12 common metrics. For metrics not in this table, set `xbrl_qname=null` — do NOT skip the item or force-fit it into a listed concept.
```

#### Edit 1F: Add non-exhaustive reminder at §13 guidance keywords (after line 531, after the keywords table)

Insert after the keywords table (after line 531):

```
These keywords are common signals, not an exhaustive filter. Extract guidance regardless of whether the source text uses these specific words.
```

---

### File 2: `.claude/agents/guidance-extract.md`

#### Edit 2A: Add §4/§7 to Step 3 (insert after line 84)

Current line 84:
```
Apply per-source profile rules (loaded in auto-load step), quality filters from SKILL.md §13, and existing Guidance tags (from Step 1) to reuse canonical metric names.
```

Insert after line 84 (before "For each guidance item, extract:"):

```
**Metric decomposition (SKILL.md §4)**: Split qualified metrics into base `label` + `segment`. Business dimensions (product, geography, business unit) become `segment`; the base metric stays as `label`. Accounting modifiers (Cost of, Net, Adjusted, Pro Forma) stay part of `label`. This ensures all segment variants share one Guidance parent node.

**Segment rules (SKILL.md §7)**: Default segment is `Total`. Set segment only when text qualifies a metric with a business dimension. Segment text feeds member matching (Step 4 pt.5).
```

#### Edit 2B: Add non-exhaustive note to instant labels (line 100)

Current line 100:
```
**Rules**: Set as many fiscal fields as text supports. `sentinel_class` ONLY when ALL fiscal fields are null (4-way judgment call). Known instant labels: `cash_and_equivalents`, `total_debt`, `long_term_debt`, `shares_outstanding`, `book_value`, `net_debt`.
```

New:
```
**Rules**: Set as many fiscal fields as text supports. `sentinel_class` ONLY when ALL fiscal fields are null (4-way judgment call). Known instant labels (not exhaustive — classify any balance-sheet stock metric as instant): `cash_and_equivalents`, `total_debt`, `long_term_debt`, `shares_outstanding`, `book_value`, `net_debt`.
```

---

### File 3: `.claude/agents/guidance-qa-enrich.md`

#### Edit 3A: Add §4 to NEW ITEM action in Step 4 verdict table (line 78)

Current line 78:
```
| `NEW ITEM` | Q&A contains guidance not in any existing item | Create new item with `[Q&A]` quote prefix. |
```

New:
```
| `NEW ITEM` | Q&A contains guidance not in any existing item | Create new item with `[Q&A]` quote prefix. Apply metric decomposition (SKILL.md §4) — split qualified metrics into base `label` + `segment`. |
```

---

### File 4: `.claude/skills/guidance-inventory/reference/PROFILE_TRANSCRIPT.md`

#### Edit 4A: Add speaker scope clarification (after line 52, after the hierarchy table)

Insert after the hierarchy table (after the `| Skip | **Operator** |` row):

```
↳ Priority sets precedence for conflicts, not scope. Extract guidance from all speakers.
```

---

## What We Are NOT Changing

- **`guidance_ids.py`** — `build_guidance_ids()` stays as-is. It takes `label` and produces `guidance_id = f"guidance:{label_slug}"`. Once the LLM sends the correct decomposed label, the code produces the correct ID.
- **`guidance_write_cli.py`** — Concept inheritance code (lines 197-205) stays as-is. It already copies `xbrl_qname` between items with the same `label`. Once labels are correct, it works.
- **`guidance_writer.py`** — MERGE templates stay as-is.
- **No hardcoded metric lists in code** — the 12 canonical metrics live only in SKILL.md §4, used by LLM judgment.
- **No deterministic string manipulation** — no regex, no prefix stripping, no code-level decomposition.

---

## Verification

1. **Dry-run test**: After edits, spawn `guidance-extract` agent on one AAPL transcript (e.g., `AAPL transcript AAPL_2025-07-31T17.00.00-04.00 MODE=dry_run`). Check CLI output:
   - All segment Revenue items should have `guidance_id = "guidance:revenue"` (not `guidance:iphone_revenue`)
   - Segment field should be `"iPhone"`, `"iPad"`, etc. (not `"Total"`)
   - "Cost of Revenue" (if present) should stay as `label="Cost of Revenue"`, `segment="Total"`

2. **Issue #27 check**: Services Revenue item should now have `label="Revenue"`, `segment="Services"` (not `segment="Total"`)

3. **Concept inheritance check**: In dry-run output, all Revenue segment items should inherit `xbrl_qname` from the Total Revenue item (concept inheritance works because labels now match)

---

### ISSUE 28 (Medium): Sonnet vs Opus quality comparison — not yet tested

**Goal**: Determine whether Sonnet 4.6 produces comparable extraction quality to Opus 4.6 for guidance extraction. If quality is close enough, Sonnet would significantly reduce cost and latency per run (~3-5x cheaper, ~2x faster).

**Test plan**:
1. Pick one transcript with known-good Opus results (e.g., `AAPL_2023-11-03T17.00.00-04.00` — 10 items, 5 Q&A enriched, richest run)
2. **Run A (Sonnet)**: Set `model: sonnet` in `guidance-extract.md` and `guidance-qa-enrich.md` frontmatter. Run full two-invocation pipeline in `dry_run` mode. Save CLI output.
3. **Run B (Opus)**: Restore `model: opus` in both agents. Run same transcript in `dry_run` mode. Save CLI output.
4. Compare side-by-side on these dimensions:

| Dimension | What to check |
|---|---|
| **Recall** | Same item count? Any missed metrics? |
| **Precision** | Any false positives (actuals, analyst estimates, factors-as-standalone)? |
| **Metric decomposition** | Correct label/segment split per §4? |
| **Numeric accuracy** | Same low/mid/high values? Double-scaling bug (Issue #20/A)? |
| **Unit canonicalization** | Correct unit_raw passed to CLI? |
| **Basis assignment** | Correct explicit-only basis, or over/under-assigning? |
| **Period resolution** | Same fiscal_year/fiscal_quarter/period_scope? |
| **XBRL matching** | Same xbrl_qname and member_u_ids? |
| **Q&A enrichment** | Same enrichment rate? Same verdicts? |
| **Quote quality** | Verbatim? Correct [PR]/[Q&A] prefix? Within 500 chars? |
| **Conditions** | Same conditions captured? FX/tariff correctly folded? |
| **Token usage** | How much cheaper is Sonnet? |
| **Latency** | How much faster? |

**Files to modify for Sonnet run**: `guidance-extract.md` line 13 (`model: opus` → `model: sonnet`), `guidance-qa-enrich.md` line 13 (`model: opus` → `model: sonnet`). Restore after.

**Status**: Open — not yet run.

4. **Existing data**: Old Guidance nodes (`guidance:iphone_revenue` etc.) remain untouched. New data writes to `guidance:revenue`. No collision, no data loss. Old orphaned nodes can be cleaned up separately.

---

## Issues Tracker Update

After implementation, update `.claude/plans/guidance-extraction-issues.md`:
- Issue #26: Status → **Fixed**
- Issue #27: Status → **Fixed** (§4 decomposition + §7 segment rules now referenced)

---

## DB Audit — 2026-03-01

Full Neo4j audit of all Guidance, GuidanceUpdate, and GuidancePeriod nodes and relationships. Cross-referenced against `guidanceInventory.md` v3.1 spec and `guidance-period-redesign.md` v3.0.

### Current DB State

| Entity | Count |
|---|---|
| GuidanceUpdate nodes | 47 |
| GuidancePeriod nodes | 8 (6 calendar + 2 sentinels) |
| Guidance nodes | 10 |
| UPDATES edges (GU→Guidance) | 47 |
| HAS_PERIOD edges (GU→GuidancePeriod) | 47 |
| FOR_COMPANY edges (GU→Company) | 47 |
| FROM_SOURCE edges (GU→Transcript) | 47 |
| MAPS_TO_CONCEPT edges | 40 |
| MAPS_TO_MEMBER edges | 9 |
| Constraints | 3 (guidance_id_unique, guidance_update_id_unique, guidance_period_id_unique) |

### What passed audit

- Every GuidanceUpdate has exactly 1 HAS_PERIOD edge (cardinality constraint per D2 met)
- Every GuidanceUpdate has FOR_COMPANY, UPDATES, FROM_SOURCE edges (100% coverage)
- No old `:Period` nodes linked to GuidanceUpdate (clean migration from #16 held)
- GuidancePeriod format correct (`gp_` prefix, calendar month-boundary dates per D8)
- `period_scope` and `time_type` populated on all 47 GuidanceUpdate nodes
- Legacy `period_type` field is null (not carried forward — correct)
- All 3 uniqueness constraints exist
- Calendar dates correct for AAPL FYE Sep (e.g., Q1 FY2024 = `gp_2023-10-01_2023-12-31`)
- 7 GuidanceUpdate nodes for custom metrics (`tariff_cost_impact` x3, `us_investment_spending` x3, `share_repurchase_authorization` x1) lack MAPS_TO_CONCEPT — acceptable, no standard XBRL concept exists for these

### Issue #44 — Sentinel GuidancePeriod nodes `gp_ST` and `gp_MT` missing (Issue #25 regression)

**Priority**: Medium
**Status**: Open

**What DB shows**: Only 2 of 4 sentinel GuidancePeriod nodes exist: `gp_LT` and `gp_UNDEF`. Nodes `gp_ST` and `gp_MT` are absent.

**Why this is an issue**: `guidance-period-redesign.md` D2 requires all 4 sentinels pre-created via `create_guidance_constraints()`. Issue #25 originally fixed this — "Only `gp_MT` existed. Fixed: `gp_ST`, `gp_LT`, `gp_UNDEF` created. All 4 sentinels + 5 calendar periods = 9 GuidancePeriod nodes verified."

**Root cause**: Run 7 performed a clean-slate deletion (Step 10 of redesign plan: "Deleted 31 GuidanceUpdate, 11 Guidance, 7 Period nodes"). The deletion removed ALL prior GuidancePeriod nodes. Run 7's re-extraction only re-created sentinels that items actually linked to (`gp_LT` for capex long-term guidance, `gp_UNDEF` for share_repurchase and capex duplicate). `gp_ST` and `gp_MT` were not linked by any Run 7 items, so they were not re-created. `create_guidance_constraints()` (which pre-creates all 4) was not re-run after the clean-slate.

**Validation**: Run `MATCH (gp:GuidancePeriod) WHERE gp.id IN ['gp_ST', 'gp_MT', 'gp_LT', 'gp_UNDEF'] RETURN gp.id`. Should return 4 rows; currently returns 2.

### Issue #45 — Run 7 aggregate totals are internally inconsistent with per-transcript table and live DB

**Priority**: Low
**Status**: Open

**What document + DB show**:
- Run 7 post-mortem currently claims: **45 P1 + 6 P2-new = 51 total items**
- But the Run 7 transcript table above sums to:
  - P1 items: `10 + 6 + 6 + 5 + 8 + 8 = 43`
  - P2 new items: `0 + 0 + 0 + 0 + 2 + 2 = 4`
  - Total: `43 + 4 = 47`
- Live DB audit matches the table sum: **47 GuidanceUpdate nodes**.

**Why this is an issue**: This is a documentation-integrity issue (not a graph-schema bug). Validation baselines for regressions, acceptance criteria, and run-to-run comparisons become unreliable when the summary totals contradict both the detailed table and the actual database state.

**Validation**:
1. Recompute totals from the existing Run 7 table (manual arithmetic above).
2. Confirm DB total with `MATCH (gu:GuidanceUpdate) RETURN count(gu)` (currently 47).
3. Confirm per-source totals with:
   `MATCH (gu:GuidanceUpdate)-[:FROM_SOURCE]->(t:Transcript) RETURN t.id, count(*) ORDER BY t.id`
   (current counts: 10, 6, 6, 5, 10, 10 -> 47).

---

## DB Audit — GuidanceUpdate Null Properties (2026-02-28)

Full Neo4j audit of all GuidanceUpdate property fields. Cross-referenced against `guidanceInventory.md` v3.1 §2 (extraction fields) and `guidance-period-redesign.md` v3.0.

### DB state snapshot

| Entity | Count |
|---|---|
| GuidanceUpdate nodes | 47 |
| GuidancePeriod nodes | 8 (6 calendar + 2 sentinels) |
| Guidance nodes | 10 |
| UPDATES edges (GU→Guidance) | 47/47 |
| HAS_PERIOD edges (GU→GuidancePeriod) | 47/47 (exactly 1 per GU) |
| FOR_COMPANY edges (GU→Company) | 47/47 |
| FROM_SOURCE edges (GU→Transcript) | 47/47 |
| MAPS_TO_CONCEPT edges | 40 (7 custom metrics lack XBRL concepts — acceptable) |
| MAPS_TO_MEMBER edges | 9 |
| Constraints | 3 (guidance_id_unique, guidance_update_id_unique, guidance_period_id_unique) |

### What passed audit

- Every GuidanceUpdate has exactly 1 HAS_PERIOD edge (cardinality constraint per D2 met)
- Every GuidanceUpdate has FOR_COMPANY, UPDATES, FROM_SOURCE edges (100% coverage)
- No old `:Period` nodes linked to GuidanceUpdate (clean migration from #16 held)
- GuidancePeriod format correct (`gp_` prefix, calendar month-boundary dates per D8)
- `period_scope` and `time_type` populated on all 47 GuidanceUpdate nodes
- Legacy `period_type` field is null (not carried forward — correct)
- All 3 uniqueness constraints exist
- Calendar dates correct for AAPL FYE Sep (e.g., Q1 FY2024 = `gp_2023-10-01_2023-12-31`)

### Issue #52 — `u_id` is null on all 47 GuidanceUpdate nodes

**Priority**: Medium
**Status**: Open

**What DB shows**: Every GuidanceUpdate node has `u_id: null`. The `id` field IS populated with the correct composite ID (e.g., `gu:AAPL_2025-07-31T17.00.00-04.00:revenue:gp_2025-07-01_2025-09-30:unknown:total`).

**Why this is an issue**: `guidanceInventory.md` §1 schema and the GuidancePeriod redesign plan both show `u_id` as a standard property on GuidanceUpdate (following the convention used by Guidance and GuidancePeriod nodes where `u_id` mirrors `id`). The `_build_core_query()` Cypher template in `guidance_writer.py` likely does not include `gu.u_id = $guidance_update_id` in the SET block.

**Validation**: `MATCH (gu:GuidanceUpdate) WHERE gu.u_id IS NOT NULL RETURN count(gu)` — returns 0. Should return 47.

### Issue #53 — `label` and `label_slug` are null on all 47 GuidanceUpdate nodes

**Priority**: HIGH
**Status**: Open

**What DB shows**: Every GuidanceUpdate has `label: null` and `label_slug: null`. The metric identity IS embedded in the `id` string (e.g., `:revenue:`, `:gross_margin:`) but is not stored as a queryable property.

**Why this is an issue**: `guidanceInventory.md` §2 defines `label` (human-readable, e.g., "Revenue") and `label_slug` (canonical slug, e.g., "revenue") as core extraction fields on GuidanceUpdate. These are needed for queries like `WHERE gu.label_slug = 'revenue'`. Without them, the only way to filter by metric is string-parsing the composite `id`, which is fragile and not indexable. The `_build_core_query()` SET block or `_build_params()` in `guidance_writer.py` is not mapping these fields through, OR the extraction JSON payload from the agent is not including them.

**Validation**: `MATCH (gu:GuidanceUpdate) WHERE gu.label IS NOT NULL RETURN count(gu)` — returns 0. Should return 47.

### Issue #54 — `direction` is null on all 47 GuidanceUpdate nodes

**Priority**: Medium
**Status**: Open

**What DB shows**: Every GuidanceUpdate has `direction: null`.

**Why this is an issue**: `guidanceInventory.md` §2 defines `direction` as a required extraction field with enum values: `up`, `down`, `flat`, `range`, `qualitative_only`. This tells the consumer the directional character of the guidance (e.g., Revenue "low to mid-single digits YoY growth" = `up`; Gross Margin "46%-47%" = `range`). Without `direction`, downstream consumers can't quickly filter or sort by directional sentiment without re-parsing qualitative text. Either the LLM extraction agent is not outputting this field, or `_build_core_query()`/`_build_params()` is not including it in the Cypher SET.

**Validation**: `MATCH (gu:GuidanceUpdate) WHERE gu.direction IS NOT NULL RETURN count(gu)` — returns 0. Should return 47.

### Issue #55 — `segment_raw` and `segment_slug` are null on all segmented GuidanceUpdate nodes

**Priority**: Medium
**Status**: Open

**What DB shows**: Items like `gu:...:revenue:...:ipad`, `gu:...:revenue:...:iphone`, `gu:...:revenue:...:services`, `gu:...:revenue:...:wearables_home_and_accessories`, `gu:...:revenue:...:mac` all have `segment_raw: null` and `segment_slug: null`. The segment IS correctly encoded in the composite `id` string (the 5th colon-delimited field), but the dedicated property fields are empty.

**Why this is an issue**: `guidanceInventory.md` §2 defines `segment_raw` (verbatim, e.g., "iPhone") and `segment_slug` (canonical, e.g., "iphone") as extraction fields. These are needed for queries like `WHERE gu.segment_slug = 'iphone'`. Issues #26 and #27 (both Fixed) addressed segment decomposition in IDs and Guidance parent grouping, but the segment property values on GuidanceUpdate were never populated. Same root cause as #53 — either missing from extraction payload or not mapped in writer params.

**Validation**: `MATCH (gu:GuidanceUpdate) WHERE gu.id CONTAINS ':iphone' AND gu.segment_slug IS NOT NULL RETURN count(gu)` — returns 0. Should return at least 1.

### Issue #56 — `evhash` is null on all 47 GuidanceUpdate nodes

**Priority**: Medium
**Status**: Open

**What DB shows**: Every GuidanceUpdate has `evhash: null`.

**Why this is an issue**: `guidanceInventory.md` §2 defines `evhash` as the 16-char hex fingerprint of the value envelope (computed by `evhash16()` in `guidance_ids.py`). It enables dedup detection — two items with the same evhash from different sources represent identical guidance. Issue #8 (Closed, by design) explicitly discussed evhash behavior for iPad/WHA items sharing a fingerprint, confirming evhash IS supposed to be computed and stored. The fact that it's null on ALL nodes (including the ones from #8's scenario) means the writer is not computing or persisting it.

**Validation**: `MATCH (gu:GuidanceUpdate) WHERE gu.evhash IS NOT NULL RETURN count(gu)` — returns 0. Should return 47.

### Issue #57 — All numeric fields (`value_low`, `value_high`, `value_point`) null on all 47 GuidanceUpdate nodes

**Priority**: HIGH
**Status**: Open

**What DB shows**: Every GuidanceUpdate has `value_low: null`, `value_high: null`, `value_point: null`. All guidance is stored as qualitative text only.

**Why this is an issue**: `guidanceInventory.md` §2 defines these as core value fields. AAPL provides explicit numeric ranges in every earnings call for standard metrics:
- **OpEx**: "$15.3B-$15.5B" → should have `value_low: 15300, value_high: 15500, unit: m_usd`
- **Gross Margin**: "46%-47%" → should have `value_low: 46, value_high: 47, unit: percent`
- **Tax Rate**: "~16%" → should have `value_point: 16, unit: percent`
- **DPS**: "$0.26" → should have `value_point: 0.26, unit: usd`
- **OINE**: "-$250M" → should have `value_point: -250, unit: m_usd`

The Run 7 post-mortem itself confirms correct units were assigned (line 130-134: "percent for Gross Margin and Tax Rate, m_usd for OpEx, OINE..."), implying the extraction DID produce numeric values and units. But the values are not persisted to the GuidanceUpdate nodes. Either `_build_params()` is not including value fields, or the Cypher SET block omits them.

**Validation**: `MATCH (gu:GuidanceUpdate) WHERE gu.value_low IS NOT NULL OR gu.value_high IS NOT NULL OR gu.value_point IS NOT NULL RETURN count(gu)` — returns 0. Expected: at least 20+ (all items with explicit numeric guidance).

### Issue #58 — `basis_raw` is null on all 47 GuidanceUpdate nodes

**Priority**: Low
**Status**: Open

**What DB shows**: Every GuidanceUpdate has `basis_raw: null` with `basis_norm: "unknown"`.

**Why this is an issue**: `guidanceInventory.md` §2 defines `basis_raw` as the verbatim basis text (e.g., "GAAP", "reported", "constant currency") and `basis_norm` as the canonical normalization (`gaap`, `non_gaap`, `constant_currency`, `unknown`). While `basis_norm: "unknown"` is the correct default when basis isn't explicitly stated, some items DO have explicit basis references. For example, AAPL's services revenue guidance from Q2 FY2025 includes "constant currency growth comparable to December quarter (14%)" — this should have `basis_raw: "constant currency"` and `basis_norm: "constant_currency"`. The blanket `unknown` across all items suggests the extraction agent is not attempting basis classification at all.

**Validation**: `MATCH (gu:GuidanceUpdate) WHERE gu.basis_raw IS NOT NULL RETURN count(gu)` — returns 0. Should return at least a few (items with explicit basis references).

### Issue #59 — `canonical_low/mid/high` may be null when `_ensure_ids()` early-returns (pre-existing design concern)

**Priority**: Low
**Status**: Open (pre-existing design)

**What the code shows**: `guidance_write_cli.py:117` — when agent pre-computes `guidance_update_id`, `_ensure_ids()` returns immediately without calling `build_guidance_ids()`. The `build_guidance_ids()` function (in `guidance_ids.py`) is responsible for computing `canonical_low/mid/high` from raw `low/mid/high` + `unit_raw` (scale normalization, e.g., billion → millions). When skipped, these `canonical_*` keys may not exist in the item dict.

`_build_params()` at `guidance_writer.py:260-262` reads:
```python
'low': item.get('canonical_low'),    # None if key missing
'mid': item.get('canonical_mid'),     # None if key missing
'high': item.get('canonical_high'),   # None if key missing
```

The Cypher SET is unconditional (`gu.low = $low`), so `None` would overwrite any existing DB values with null on a re-run where the agent provides `guidance_update_id` but not `canonical_*` values.

**Why this matters**: If an agent pre-computes the ID but sends raw `low/mid/high` (not `canonical_*`), the writer silently drops the numeric values. No validation error, no warning. The contract assumption — "if you provide `guidance_update_id`, you must also provide `canonical_*` values" — is implicit, not enforced.

**What this is NOT**: This is not caused by the #53/#55 denormalized slug fix. The edge case existed before and after that change identically. It was surfaced during code review of `_build_params()` but is unrelated to the slug work.

**Potential fix**: Add a warning in `_build_params()` when `canonical_low/mid/high` are all None but `low/mid/high` raw values exist in the item:
```python
if item.get('low') is not None and item.get('canonical_low') is None:
    logger.warning("Item %s has raw 'low' but no 'canonical_low' — scale normalization may have been skipped", item.get('guidance_update_id'))
```

**Validation**: Check if any current agent payloads rely on the early-return path with raw numeric values. Inspect `/tmp/gu_*.json` files (if preserved) for items with `guidance_update_id` set AND `low`/`high` present but `canonical_low`/`canonical_high` absent.

### Issue #60 — No Neo4j indexes on denormalized `label_slug` / `segment_slug` properties

**Priority**: Low
**Status**: Open

**What DB shows**: `SHOW INDEXES WHERE entityType = 'NODE' AND labelsOrTypes = ['GuidanceUpdate']` returns only 1 index: the uniqueness constraint on `id`. No indexes on `label_slug` or `segment_slug`.

**Why this matters**: Issues #53/#55 added `label_slug` and `segment_slug` as denormalized properties to enable direct queries like `WHERE gu.label_slug = 'revenue'`. Without indexes, these queries do a full label scan of all GuidanceUpdate nodes. At 47 nodes this is irrelevant (~microseconds). At 10,000+ nodes across hundreds of companies, it would matter.

**Fix**: Add 2 lines to `create_guidance_constraints()` in `guidance_writer.py`:
```python
("CREATE INDEX gu_label_slug IF NOT EXISTS "
 "FOR (gu:GuidanceUpdate) ON (gu.label_slug)"),
("CREATE INDEX gu_segment_slug IF NOT EXISTS "
 "FOR (gu:GuidanceUpdate) ON (gu.segment_slug)"),
```

Or run directly via MCP:
```cypher
CREATE INDEX gu_label_slug IF NOT EXISTS FOR (gu:GuidanceUpdate) ON (gu.label_slug)
CREATE INDEX gu_segment_slug IF NOT EXISTS FOR (gu:GuidanceUpdate) ON (gu.segment_slug)
```

**Validation**: After creating indexes, `SHOW INDEXES WHERE entityType = 'NODE' AND labelsOrTypes = ['GuidanceUpdate']` should return 3 rows (id unique + label_slug range + segment_slug range).

### Likely shared root cause for #52-#58

Issues #52 through #58 (7 issues) all follow the same pattern: GuidanceUpdate properties that are defined in the spec and presumably extracted by the LLM agent are not persisted to Neo4j. The graph topology (edges, node types) is correct, but property fields are systematically empty.

Two possible failure points:
1. **Extraction payload**: The JSON written to `/tmp/gu_*.json` by the agent may not include these fields
2. **Writer pipeline**: `_build_params()` in `guidance_writer.py` may not map these fields into Cypher parameters, or `_build_core_query()` may not include them in the SET clause

To diagnose: inspect a `/tmp/gu_*.json` payload from a recent run (if preserved), or read `guidance_writer.py` `_build_params()` and `_build_core_query()` to check which fields are mapped.
