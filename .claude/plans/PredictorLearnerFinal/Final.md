# Final Predictor / Learner Target Design

- Transport: predictor, learner, and guidance extraction all use **real interactive Claude in TMUX**: launch `claude` with OAuth/subscription credentials, **never API, never SDK, never `claude -p` / `--print`**. Subscription/no-API rationale + guards: `.claude/plans/ANTHROPIC_BILLING_SUBSCRIPTION_CRITICAL.md`. Transport implementation contract: §5 / `.claude/plans/tmux-transport-handoff.md`.
- Owner decision: normal Claude subscription path is required. Use interactive TMUX (`claude`, no `-p`) despite harder engineering; do not use the easier programmatic pool path.
- Scope rule: transport is a transport-layer change only — it does not alter skill/prompt logic, result contracts, validators, folders, or renderers unless a section below explicitly overrides.
- Verified: both forked:skill and top-level embedded prompts run correctly under the interactive TMUX subscription model.

# 0. System Overview (orientation for implementer)
- Pipeline: 8-K (Item 2.02) earnings event → orchestrator builds the context bundle (7 parallel builders + sequential prior_reports_context) → predictor writes prediction/result.json → once the move is known, learner writes learning/result.json → EV1 scorer (§18) grades it → learner reports feed the next predictor's bundle (the learning loop).
- The 7 parallel builders: 8k_packet, guidance_history, inter_quarter_context, peer_earnings_snapshot, macro_snapshot, consensus, prior_financials. prior_reports_context is the logical 8th bundle field, built sequentially after the 7 (§11) — never an 8th parallel builder.
- Mode selection: historical if a pit_cutoff is set (backfill/replay), live if not (real-time trigger) — `adapters.py::_derive_mode`. Historical = forked, bundle-only, PIT-fenced (§1.1); live = embedded prompt + tools + SLA (§1.2).
- Run lifecycle: predictor runs per earnings event; learner is eligible once that event's outcome return is knowable and fires just-in-time before the next prediction for that ticker per §22 (no scheduled cron); the EV1 scorer runs deterministically over completed predictions; guidance extraction (§4) is a separate pipeline (transport-only change).
- Glossary: PIT = point-in-time (no future-data leak); pit_cutoff = timestamp bounding what a run may see; pit_boundary_event = the event whose outcome bounds the learner's hindsight; no_call = predictor declines a directional call (§7); DataSubAgent = a spawnable data-fetch sub-agent (§13); Section 10 = the prior-learner-reports block of the rendered bundle (§6); Phase 1-4 / Phase-2 questions = the predictor skill's existing analysis stages, preserved (§16).

# 1. Predictor Skill Modes
- 1.1 historical (PIT-enabled, bundle-only) · 1.2 live (parallel tool access) · 1.3 common to both

1.1 <historical> mode: 
    1.1.1: Unchanged invocation — forked `/earnings-prediction` skill (NOT embed; the fork itself blocks Data SubAgents). Transport only: current SDK/`claude -p` path → interactive TMUX. Concrete shape: TMUX Profile A launches `claude` (NO `-p`) and sends the same prompt text as today: `Run /earnings-prediction with these paths: ...`. The slash-command prompt invokes the forked skill; do NOT inline SKILL.md for historical prediction. Wire layer changes; prompt shape does not.
    1.1.2: PIT tool fence — project-level PreToolUse hook configured in `.claude/settings.json`, scoped by env marker `EARNINGS_PIT_FENCE=1`. Hook script at `.claude/hooks/earnings_pit_fence.py` reads `os.environ` at invocation; marker present → DENY listed tools, absent → pass through (concurrency-safe, per-process env scoping). Orchestrator sets the marker ONLY for the historical forked spawn (cleared on exit). Marked sessions DENY Bash, WebFetch, WebSearch, and all `mcp__*` tools (deny-by-default class matcher `mcp__.*` + hook-side `startswith("mcp__")` → covers Neo4j, IBKR, any future MCP without enumeration); unmarked sessions pass through, so live/learner/other sessions are unaffected. The new hook does NOT replace `.claude/hooks/pit_gate.py`; keep `pit_gate.py` for DataSubAgent/tool output PIT validation (separate concern, separate hook event). `earnings_pit_fence.py` is only the historical-predictor runner-level tool fence. Skill frontmatter is NOT used (skill allowed/disallowedTools is not runner-enforced). Allowed: Read, Glob; Write and Edit are DENIED unless `tool_input.file_path` ends in EXACTLY one of: `prediction/section_audit.json`, `prediction/result.json`, `prediction/reasoning.md`, or `prediction/complete.json` (path-scoped, NOT loose suffix — denies `learning/*`, `context_bundle*`, prior-reports paths, `result.md`, and any other Write target). Hook-enforced via PreToolUse `file_path` inspection — NOT prompt-only. Empirical validation: `.claude/plans/Infrastructure.md` "Project PreToolUse hook fires INSIDE `context: fork` skills" (PROVEN 2026-05-19, v2.1.144) — concurrent marked/unmarked sessions with zero cross-contamination, class matcher proven across multiple MCP namespaces in one run.
    1.1.3: Soft SLA — log elapsed only; no hard-kill; elapsed never fed to learner.
    
1.2 <live> mode: 
    1.2.1: Live SLA / urgency nudges:
        - LIVE_PREDICTOR_SLA_SECONDS controls live deadline; default 300s. LIVE_PREDICTOR_NUDGE_INTERVAL_SECONDS defaults 60s. LIVE_PREDICTOR_GRACE_SECONDS defaults 30s.
        - LIVE_PREDICTOR_SLA_MODE controls enforcement: hard|soft, default hard. hard kills TMUX after sla_seconds + grace_seconds if result.json is missing/invalid; soft only logs/nudges and never kills.
        - Env var config home: set on the process that launches live prediction; orchestrator reads via `os.environ` (k8s manifests should mirror the existing extraction-worker env pattern).
        - Clock sources: time_since_report_release uses report-release timestamp from trigger metadata (Redis if present, else Neo4j); elapsed_since_start_s uses predictor TMUX session spawn time.
        - Orchestrator queues LIVE_TIME_UPDATE every nudge interval until valid result.json exists:
          LIVE_TIME_UPDATE: time_since_report_release=<...>; price_change_since_report_release=<...>; elapsed_since_start_s=<...>; sla_seconds=<...>
        - Send nudges by typing text into session input + Enter, e.g. tmux send-keys -t <session> '<message>' Enter. This queues for the next turn; never send Esc/Ctrl-C.
        - Empirically verified: mid-generation nudge queued without interrupting/corrupting the in-flight turn.
        - At elapsed_since_start_s >= sla_seconds, queued updates tell live predictor to stop expanding research and write best available prediction.
        - In hard mode, if result.json is still missing/invalid after sla_seconds + grace_seconds, orchestrator kills the TMUX session and fails closed: no live prediction / no trade. reasoning.md is non-blocking; result.json is required.
        - No timeout no_call fallback is written. A killed/missing-result live run is operational-only: log/report as timeout health, but produce no prediction_result, no learner input, and no prior-report row.
    1.2.2: Tool Calls: 
        1.2.2.1: Live tool discipline is prompt-only for now; no runner-level tool-gating change here. The §2.1 "Live allowed research set" is prompt-level guidance, not a runner-enforced allowlist. See SKILLS / Predictor skill.
        1.2.2.2: Parallel tool calls:
            Prompt to make any skill (predictor incl.) do parallel tool calls:
            These N analyses are INDEPENDENT — none uses another's output.
            Spawn all N sub-agents; do NOT wait for any result before issuing the next; collect results after all are dispatched.
            Primary driver (best-supported, not isolated by a control): task independence (model only blocks when it needs a prior result). "Don't wait/block" is a recommended reinforcing instruction, not independently proven necessary. Single-message batching is NOT the lever and is not achievable by instruction — the model emits one spawn per turn (~1s apart) and they still run concurrently. Expected; do not engineer single-message batching. Why this works: the harness runs each spawned sub-agent asynchronously and the issuing session does not block, so agents started ~1s apart overlap and run concurrently.
    1.2.3 Invocation shape:
        - Live predictor uses learner-style top-level embed: load earnings-prediction/SKILL.md into the main prompt, then append live wrapper instructions/tools/SLA.
        - Live wrapper minimum: `PIT_MODE=live`, report-release timestamp, SLA/env values (§1.2.1), live allowed research set (§2.1), no runner-enforced tool allowlist (§1.2.2.1), required output paths, and fail-closed `result.json` rule.
        - Do not invoke /earnings-prediction as a forked skill in live mode; forked skill is historical-only.

1.3 <common to both modes>: 
    1.3.1 One shared base predictor skill; the orchestrator applies the mode split (historical per §1.1, live per §1.2). No separate predictor skills.
    1.3.2 Urgency inputs: pass time_since_report_release and price_change_since_report_release to both modes. Historical uses PIT-safe values at launch; live receives queued LIVE_TIME_UPDATE nudges per 1.2.1.
    1.3.3 Reasoning sidecar:
        - Add REASONING_PATH=<component>/reasoning.md for historical prediction, live prediction, and learner.
        - reasoning.md is audit-only: never canonical, never parsed for scoring/learning, and missing reasoning.md does not fail the run. result.json remains required.
        - Predictor prompt: before RESULT_PATH, write Phase 1-4 working analysis to REASONING_PATH: key numbers/surprise math, what's-new/priced-in/material/counter-case, bull vs bear, final rationale, with bundle evidence.
        - Learner prompt: before RESULT_PATH, write causal-attribution analysis to REASONING_PATH: what moved stock, evidence chain, primary vs contributing drivers, reconcile vs prediction including the §15 falsifier check, attribution gaps, key_takeaway rationale, and checklist rewrite rationale, with ledger refs.
        - Skill rule edits: predictor checklist rule 8 may write SECTION_AUDIT_PATH + REASONING_PATH + RESULT_PATH; learner must relax both single-file guards (Critical Rule 6 + step "ONLY file" rule) to allow REASONING_PATH + RESULT_PATH.
        - Keep thinking.md/subagents unchanged; ignore thinking.md as reasoning. Learner validator + result.md renderer + orchestrator lesson surfaces are torn down to match §8 (no predictor_lessons/global_observations/lesson_audit).

# 2. SKILLS
- SKILL rewrite discipline: when rewriting `.claude/skills/earnings-prediction/SKILL.md` and `earnings-learner/SKILL.md`, weave design rules (§7/§9/§12/§15/§16/§18) into existing SKILL phases as terse clauses; do NOT add new "Principles" blocks, schemas, taxonomies, telemetry, benchmark tables, hardcoded examples, or other machinery. EV1 deterministic scoring (§18) lives in code, never in SKILL prompts.
- SKILL rewrite is strictly subtractive: remove only lesson machinery; preserve each current SKILL.md analytical/causal-attribution spine and every non-lesson instruction verbatim unless this design explicitly overrides. Prior-report/checklist replacements must not reintroduce lesson-shaped structure: per-item labels, IDs, audit, scope routing, or lifecycle state.

## 2.1 Predictor skill
- Live mode has no PIT restriction, but is urgency/attention constrained: bundle is the primary substrate; live sources are targeted gap-fills only, used only if they can plausibly change direction, confidence, range, falsifier, or no_call — no fishing expeditions.
- Live allowed research set: existing DataSubAgent families (Neo4j report/transcript/xbrl/news/entity/vector-search; AlphaVantage/Yahoo/BZ news; Perplexity ask/search/reason/research) plus live-specific direct tools when needed (WebFetch/WebSearch, Neo4j read, IBKR market data).
- Prefer parallel independent checks; avoid tool-chasing; stop when evidence is sufficient.
- Live tools are read/query/fetch only; never write or mutate production stores (Neo4j, orders, or disk outside explicit output paths).
- No numeric live tool-call cap; the env-configurable time SLA is the sole hard governor. Use judgment/frugality under §1.2.1, not a fixed call count.

# 3. Learner
- Keep the learner's embed shape (top-level embedded prompt loading earnings-learner/SKILL.md, not forked) and its ungated tool surface; transport changes current SDK/`claude -p` path → interactive TMUX (`claude`, no `-p`) per §0/§5. The ONLY rewrite is the skill prompt/output contract: from the current `attribution_result.v3` lesson-lifecycle → §8 `learner_result.v1` + §12 methodology (no managed lesson lifecycle).
- Learner may use DataSubAgents/tools, governed by §9 (PIT fence) + §12 (methodology).
- Add REASONING_PATH per 1.3.3.

# 4. Guidance Extraction
- Move guidance extraction to TMUX CLI subscription transport.
- Transport-only change: preserve existing prompts, outputs, validators, folders, and renderers.
- Apply same no-API / subscription-only guard as predictor/learner.
- Extraction worker TMUX scope: refactor the single Claude invocation path in `scripts/extraction_worker.py` from SDK/`claude -p` to interactive TMUX (`claude`, no `-p`) for all extraction job types the worker handles. Today only `guidance` is implemented/enqueued, but future extraction types inherit the same TMUX transport automatically; do not special-case guidance-only. Deployment scale/KEDA state is operational, not design.

# 5. TMUX Transport
- Use `.claude/plans/tmux-transport-handoff.md` as the implementation contract for TMUX CLI subscription transport.
- Implement the handoff §6 build scope only; cite §7 evidence, do not rerun experiments.
- Hard billing/auth rule: all profiles launch `claude` interactively inside TMUX with OAuth credentials and `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` stripped. `claude -p`, `--print`, `claude_agent_sdk.query`, and direct Anthropic API calls are forbidden target paths because they use the programmatic pool/API path, not the normal interactive subscription path.
- Profile mapping: Profile A = interactive TMUX without planned mid-run nudges; Profile B = interactive TMUX with nudge/SLA loop. Historical predictor = Profile A; live predictor = Profile B; learner/guidance = Profile A unless nudges are explicitly needed.
- Preserve user-authorized launch, no-API env scrub, pinned session id, transcript path derivation, transcript capture, timeout/kill, and text+Enter-only nudge rules.
- Large outputs must capture stdout/transcript to files; never use tmux pane scrollback as canonical output. Verify large bundles, 8-K packets, and learner evidence are not truncated before E2E — silent truncation = corrupted artifact.

## 5.1 Claude Subscription Usage Gate
- **Current anchor:** guidance extraction already gates Claude usage in `scripts/extraction_worker.py`, not `scripts/guidance_trigger_daemon.py`: pre-flight usage refresh via `scripts/claude_usage_fetch.py` + cached `logs/claude-usage/claude_usage_summary.json`; in-flight `"hit your limit"` detection requeues without retry penalty.
- **Target:** centralize this as one shared usage-gate module used by every Claude-consuming worker/process: guidance extraction, predictor, learner, earnings-worker (§22), and future Claude workers. Trigger daemons enqueue only; the process about to start a Claude session (worker or orchestrator) must call the shared gate.
- **Subscription policy:** a dedicated Claude subscription is allocated to this project's automated jobs, separate from other personal/interactive Claude use. Default policy for the dedicated subscription = full capacity (no daily reserve / no days-until-reset throttling).
- **Failover policy:** if the dedicated subscription is exhausted, the shared gate automatically switches to another configured Claude subscription/account (no manual intervention), then applies reserve/tier throttling to protect fallback capacity.
- **Account profiles:** each configured Claude subscription/account is an isolated Claude home directory containing its own `.claude/.credentials.json`; the shared gate checks profile-scoped usage cache and launches both `claude_usage_fetch.py` and TMUX Claude sessions with `HOME=<profile_home>`. Never mutate/symlink global `~/.claude/.credentials.json` at runtime; switching is per-process env only.
- **Gate mechanics:** shared gate owns usage cache refresh, pre-flight wait/sleep, and in-flight rate-limit detection. Jobs paused or requeued for rate limits do NOT count as failures and do NOT burn retry budget.
- **Priority under constraint (tier order, highest → lowest):** live prediction / current-event blockers first; just-in-time learner blocking the next prediction second; historical prediction/learning catch-up third; bulk guidance/backfill/future agents last. Lower tiers pause first.
- **Implementation target:** create one shared module, e.g. `scripts/claude_rate_gate.py`; refactor `scripts/extraction_worker.py` to use it; new predictor/learner/earnings workers MUST import it instead of duplicating gate logic. Extend the usage fetch/gate path to support configured subscription/account profiles. Under the dedicated subscription, set `DAILY_INTERACTIVE_PCT=0` and `DAILY_INTERACTIVE_PCT_SONNET=0` (keep vars present so reserves re-enable on fallback).

# 6. Prior Learner Reports
- Predictor receives prior learner reports, not prior predictor reports: summary rows from `learning/result.json`, full open via allowlisted `learning/result.md`.
- Visible rows: up to 12 own-ticker learner reports + up to 4 peer learner reports.
- Peer report candidates use the existing deterministic peer universe: same Neo4j Industry via `BELONGS_TO`, ranked by `Company.mkt_cap`; never LLM-selected and never widened to sector. Show up to 4 PIT-visible peer learner reports; if fewer exist, show fewer.
- Forced opens: latest 4 own first, then up to 2 most-recent own misses not already opened. Miss = directional call (long/short) with direction_correct == false; no_call is not a miss (per §18). Miss-priority is own-ticker only.
- Optional opens after forced set: older own and up to 3 peer reports by the predictor's own judgment of summary-row relevance.
- Historical uses PIT-safe allowlist; live has no PIT restriction but still uses orchestrator-provided allowlist.
- Validator checks opened report IDs are allowlisted, forced own/miss IDs are opened, peer opens ≤3, no duplicates, and no current-event self-leak. Cross-file invariant: every `forced_open_ids[]` entry from the bundle MUST appear in `prediction_result.opened_prior_reports[]`.
- Render Section 10 as a bulleted list per report, not a table.
- Each report bullet shows: Ticker + Quarter + Date; predicted_direction vs actual_direction + direction_correct/miss + actual_return_pct; quoted key_takeaway; Link to allowlisted `learning/result.md`.
- Do not render tags, lesson labels, or audit history.
- Machine source is `learning/result.json`; `result.md` is read-only prose for the predictor. If `result.md` is missing, regenerate from `result.json`, never parse markdown as source truth.
- Container shape (`prior_reports_context`): JSON envelope built by the orchestrator at bundle-assembly time; rendered into the predictor bundle per §11. Field names below are the contract — implementer must match exactly. Per-row enum values (direction, etc.) follow §7.
- Ordering: `own_reports[]` recency-desc; `peer_reports[]` mkt_cap-desc per §6 peer universe. `forced_open_ids[]` is an independent required-open set (latest 4 own + ≤2 most-recent own misses) and MUST NOT reorder `own_reports[]`; forced misses may appear anywhere within the recency-desc list.

```
prior_reports_context = {
  "generated_at":                 "<ISO8601>",
  "pit_cutoff":                   "<ISO8601>",
  "target_ticker":                "<str>",
  "target_quarter_label":         "<str>",
  "forced_open_ids":              ["<report_id>", ...],
  "_allowed_prior_report_paths":  ["<learning/result.md path>", ...],   // orchestrator-built read allowlist; validator ensures every opened_prior_reports[] ID maps to a row whose result_md_path is in this set; per §17 rename from _allowed_learner_paths
  "future_checklist":             ["<question string>", ...],   // transient copy of latest eligible own learner result's future_checklist[] per §8/§12
  "own_reports":                  [<prior_report_row>, ...],
  "peer_reports":                 [<prior_report_row>, ...]
}

prior_report_row = {
  "report_id":               "<str>",
  "ticker":                  "<str>",
  "quarter_label":           "<str>",
  "report_date":             "<ISO8601>",   // prior event's filed_8k from §8; NOT attributed_at
  "predicted_direction":     "<enum per §7 `direction` field; renamed in this row for clarity vs `actual_direction`>",
  "expected_move_range_pct": [<float low>, <float high>],   // unsigned magnitudes per §18; sign from predicted_direction
  "actual_direction":        "<enum>",
  "actual_return_pct":       <float, signed>,
  "direction_correct":       <bool | null>,   // null when predicted_direction == no_call per §18
  "key_takeaway":            "<str, quoted from learner result>",
  "result_json_path":        "<path to allowlisted learning/result.json>",   // machine source per §6
  "result_md_path":          "<path to allowlisted learning/result.md>"
}
```

# 7. Prediction Result Schema
- Canonical artifact: `prediction/result.json`, schema `prediction_result.v1`.
- Orchestrator-stamped fields: schema_version, ticker, quarter_label, predicted_at, model_version, prompt_version, sdk_session_id nullable, pit_mode, prediction_delay_sec, confidence_bucket, magnitude_bucket.
- LLM-authored fields: direction, confidence_score, expected_move_range_pct [low, high], key_drivers[], data_gaps[], evidence_ledger[], analysis, falsifier, opened_prior_reports[].
- `direction` enum: `long` | `short` | `no_call`.
- Drop lesson_labels and cites_lesson_indices.
- Remove old lesson-label plumbing from predictor skill: lesson_labels, cites_lesson_indices, [reviews/status] tags, global_observations. Keep the mechanism-discipline (apply a prior finding only if its cause-effect is present in this quarter), re-pointed from lessons to §6 prior-learner reports. Context-Only block is superseded by §6 + §8 (no capability lost).
- No LLM point estimate: scorer derives midpoint from expected_move_range_pct.
- key_drivers[] shape: `{driver, direction: long|short, evidence:[SRC ids]}`. Drivers are short causal phrases; no controlled vocabulary/tags.
- `opened_prior_reports[]` shape: `list[str]` of `report_id` values matching §6 `prior_report_row.report_id`.
- `evidence_ledger[]` shape: list of `{metric, value, source, source_id}` entries. Same shape reused by learner per §8.
- analysis is the concise canonical thesis: bull case, bear case, and final rationale.
- falsifier is a single primary observable thesis-breaker; required for directional calls, null for no_call.
- `no_call` has two valid paths: Balanced = at least one grounded long driver and one grounded short driver survive review; Missing-data = data_gaps[] non-empty and analysis explains why missing data prevents a call.
- Invalid directional calls fail validation/retry; validator must not silently convert them to no_call.
- prediction_delay_sec is live-only; null in historical or if filed_8k unavailable.
- result.json is required and machine-canonical; reasoning.md is fuller audit-only working analysis per 1.3.3.

# 8. Learner Result Schema
- Canonical artifact: `learning/result.json`, schema `learner_result.v1`.
- Learner writes causal attribution, not managed lesson lifecycle state.
- Orchestrator-stamped fields: schema_version, ticker, quarter_label, filed_8k, accession_8k, attributed_at, model_version, sdk_session_id nullable, pit_mode, pit_cutoff, pit_boundary_source, pit_boundary_event, actual_return_pct, context_bundle_ref, prediction_result_ref.
- LLM-authored fields: evidence_ledger[], primary_driver, contributing_factors[], feedback{prediction_vs_actual, why, what_worked, what_failed}, key_takeaway, future_checklist[], missing_inputs[], data_sources_used[].
- key_takeaway is exactly one descriptive sentence for prior-report rows: decisive realized driver(s), prediction hit/miss why, and future relevance handle. No directive, no evidence IDs, no semantic validator.
- future_checklist[] contains prediction-time-checkable questions only; never hindsight answers or evidence.
- primary_driver shape: `{driver, evidence:[evidence_ledger.source_id]}`.
- contributing_factors[] shape: `{factor, evidence:[evidence_ledger.source_id]}`.
- feedback.what_worked[] and feedback.what_failed[] are plain strings; evidence support comes through learner evidence_ledger[].
- feedback.prediction_vs_actual and feedback.why are plain LLM-authored prose strings; no scorer-owned numbers (direction_correct, magnitude_error, etc.) — those live in §18.
- future_checklist[] is a list of plain strings.
- missing_inputs[] shape: `[{input}]`.
- data_sources_used[] is a list of plain strings.
- evidence_ledger[] uses the same shape as predictor: `{metric, value, source, source_id}`.
- Learner evidence grounding is INTERNAL: every primary_driver/contributing_factors evidence ref must resolve in the learner's own evidence_ledger[], which the learner must populate with every source it used (incl. post-event transcript/news); no source → no claim. §10's bundle-catalog grounding is predictor-only and does NOT apply to the learner.
- Scorer-owned (not learner-authored): graded numbers such as direction_correct, magnitude_error, MSE, Brier; plus derived fields such as actual_direction (per §18).
- result.json is required and machine-canonical; reasoning.md is fuller audit-only attribution analysis per 1.3.3.

# 9. Learner PIT / Future Checklist Fence
- Learner may use hindsight evidence for attribution only if evidence is available before the learner boundary event; exclude the boundary event itself and anything after it.
- Predictor may see a learner report only when `learner_result.pit_cutoff <= predictor.pit_cutoff` for that predictor run.
- `future_checklist[]` must be outcome-neutral, prediction-time-checkable questions; never hindsight answers or evidence.
- No semantic checklist validator; enforce by prompt + shape gate only.

# 10. Evidence Grounding
- Historical: every `evidence_ledger[].source_id` must resolve in the PIT-safe bundle catalog.
- Historical: every `key_drivers[].evidence[]` ID must resolve in the same catalog; key driver prose stays free-form, no semantic validator.
- Directional calls require at least one supporting current-event/current-bundle evidence ID. Prior reports, checklist items, falsifier, and data_gaps never count as evidence.
- No numeric evidence floor beyond that current-event anchor.
- If a numeric floor is ever added later, count unit = distinct resolving SRC IDs across supporting key_drivers.
- Live mode: defer `SRC:LIVE:*` runtime catalog. Until built, live grounding is weaker: live-only facts in `evidence_ledger[]` or `key_drivers[].evidence[]` may carry provider/source detail but do not get strict runtime-ID validation.

# 11. Prior Reports Build Placement
- Build `prior_reports_context` sequentially after the 7 parallel context builders finish and before evidence catalog/rendering.
- Rewrite the existing `build_learning_context` slot/body into `build_prior_reports_context`; do not add an 8th parallel builder.
- Discovery source: candidate prior reports are enumerated by filesystem glob `earnings-analysis/Companies/*/events/*/learning/result.json`; NOT `run_ledger` (operational bookkeeping, not artifact source truth).
- Rename lesson-era surfaces: `#S10.lesson.L<n>` → `#S10.report.R<n>` for prior-report locator IDs (not directional evidence); `_allowed_learner_paths` → `_allowed_prior_report_paths`; rendered `learner_result:` labels become prior-report links.
- PIT-safe selection: include a learner report only if `learner_result.pit_cutoff <= consuming predictor's pit_cutoff`; always exclude the current event's own learner report.
- Any future-leak/self-leak violation in a selected/forced report halts the run. Missing/corrupt old learner files may be logged and skipped/degraded to empty schema-consistent context.
- The final rendered bundle passed to predictor must include the complete prior_reports_context.

# 12. Learner Methodology
- Preserve learner investigation depth and evidence discipline; replace managed lesson generation with causal attribution.
- Workflow: read prediction, bundle, prior reports + carried standing checklist, and actual return; scan the bundle to fix the observability boundary (what the predictor could see); fetch post-event evidence; explain the whole stock move (§15); compare prediction thesis and falsifier vs actual outcome; write attribution, key_takeaway, and rewrite the rolling `future_checklist`.
- Learner edge-mining funnel: (1) isolate from §15 the part of the move the predictor got wrong, under-weighted, or correctly caught but should preserve; (2) knowable-test — was a signal derivable from information the predictor was allowed to use? if not, it is not a future edge; (3) attack the survivor — would it have changed or strengthened the call, is it repeatable vs one-off, and is it answerable next time? Examine all information the predictor could access; never limit to one source type.
- D8 output rule: a surviving edge enters future_checklist[] only as a prediction-time-checkable question answerable from the next predictor's allowed bundle. Post-event-only insight with no predictor-visible proxy is omitted, or kept as a non-evidence company-history caution — never as evidence.
- Do not write predictor_lessons, data_lessons, global_observations, or lesson_audit.
- Cross-ticker/sector generalization moves to §6: predictor learns from own + peer learner reports at prediction time, not from learner-authored global rule objects.
- Standing checklist: `future_checklist[]` is one rolling own-ticker checklist stored only inside the latest eligible learner result; orchestrator surfaces it into the next predictor bundle. No separate store, IDs, per-item lineage, source links, scores, labels, keep/drop state, or lifecycle machinery.
- Learner rewrites `future_checklist[]` whole each cycle, consolidating from the same PIT-visible own-ticker prior-report window §6/§11 already surfaces; no separate review-window N, peer/industry checklist merging, stored cross-report synthesis, or per-company "what works" profile.
- Predictor engages relevant checklist items inside `analysis` prose; dismisses irrelevant items in one line; do not add `checklist_review[]`.
- Anti-forgetting: keep durable recurring-conditional questions even when the condition is absent this quarter; remove only items that are generic, stale, redundant, or one-off — not items whose recurring condition was simply absent this cycle.
- Length policy: no fixed numeric cap. Items must be interrogative questions, not directives or answers; ticker-specific; concise; prediction-time-checkable from the predictor's allowed bundle. Checklist items focus attention only and never substitute for §10's current-event/current-bundle evidence requirement.

# 13. DataSubAgent / Parallelism Contract
- DataSubAgents require top-level embed/TMUX context; forked predictor skill cannot be used for live/DataSubAgent mode.
- Top-level TMUX interactive runs are empirically proven to access Agent/DataSubAgents and run independent spawned agents concurrently; see `.claude/plans/tmux-transport-handoff.md`.
- Parallelism rule: spawn independent, self-contained tasks without waiting; one spawn per turn (~1s apart) is expected and still runs concurrently; single-message batching is not the lever.
- DataSubAgent availability is empirically proven in `.claude/plans/tmux-transport-handoff.md`; implementation should reuse that contract and include/keep a startup smoke check before DataSubAgent-dependent runs.

# 14. Gap / Failure Field Boundaries
- Predictor `data_gaps[]`: material pre-outcome inputs unavailable to predictor; shape `[{gap}]`; required only for missing-data no_call, otherwise optional. Used for confidence/range/no_call, never evidence.
- Learner `missing_inputs[]`: post-outcome evidence unavailable to learner that would improve attribution/checklist; not copied from predictor data_gaps; never evidence.
- Learner `feedback.what_failed[]`: available-to-predictor information that predictor ignored, misread, or under/over-weighted; cap ≤3; evidence-grounded via learner ledger refs.
- These fields are disjoint.

# 15. Whole-Move Attribution
- Learner must explain the whole stock move, not just the earnings/fundamental story.
- Treat cause families as prompt lenses only, not schema enums/fields: fundamentals, guidance, one-time/cosmetic, positioning/expectations, macro/sector, peer read-through, analyst/news, flow/technical, unexplained residual.
- `primary_driver` is the single dominant sourced mechanism, grounded per §8 (learner-internal ledger); non-fundamental causes may be primary.
- `contributing_factors[]` covers up to 3 secondary sourced forces/offsets, grounded per §8 (learner-internal ledger).
- Attribution is a bounded loop: hypothesize drivers, test whether they explain the move's sign and magnitude, return to evidence for contributors/offsets when a gap remains, and stop when the explanation stops changing materially; only the genuine sourced remainder becomes unexplained residual.
- If part of the move remains unsupported after a genuine sourced attribution attempt, state `unexplained residual` in `feedback.why`; never invent a cause or residual percentage, and never use residual as a substitute for attribution the bundle/live sources could support.
- If part of the move stays unexplained, only add it to `future_checklist[]` when the next predictor's bundle will contain data that can detect the same cause next time (§12 D8 rule). Otherwise leave it as residual — never add a checklist question the predictor can't answer from its bundle.
- Falsifier check: explicitly verify whether the prediction's stated `falsifier` (§7) was triggered by the realized move; record the answer in `feedback.what_failed[]` (fired) or `feedback.why` (did not fire or not applicable) — no new schema field.

# 16. Predictor Methodology
- Preserve predictor analytical spine/order: read full bundle; write section audit scoped per `section_audit_scope[]` (see next bullet); open/read §6 prior reports per forced/optional rules, engage relevant §12 checklist questions, and record `opened_prior_reports[]`; extract key numbers/surprise quality; answer Phase-2 questions; stress long vs short; then call.
- Section audit scope: bundle exposes top-level `section_audit_scope[]` containing current-event factual section names. SKILL audits exactly that set, NOT hard-coded section numbers. Excludes `prior_reports_context` / checklist memory and any future memory-class section.
- Market-grading lens is a bounded loop: form a candidate lens, test it against allowed bundle/live signals, prior own reports, peer reactions, analyst/management emphasis, price setup, and surprise math; revise until the lens stops changing materially or the live SLA requires a call, then rank signals against it.
- Derive the lens per print; never hardcode metric maps/examples.
- Historical mode must not use post-cutoff transcript/Q&A or other hindsight evidence; live mode may use live evidence within §1.2/§2.1 urgency rules.
- Current-bundle peer reactions may inform the lens; prior learner reports only provide context within §6/§9 and never replace current-event evidence.
- Stress-test: what's new, what's priced in, what's material, strongest counter-case, top drivers.
- If evidence is thin, conflicting, or missing, lower confidence, widen range, use data_gaps, or choose no_call; never invent a sector metric.
- Output only through §7 schema + §1.3.3 reasoning sidecar; no new predictor fields or semantic validators.

# 17. Current Code Anchors
- Orchestrator core: `scripts/earnings/earnings_orchestrator.py` — `build_prediction_bundle`, `run_core_flow`, `get_prediction_paths`, `build_evidence_source_catalog`, `validate_prediction_result`, `finalize_prediction_result`, `_resolve_pit_mode`, `_build_predictor_prompt`, `_build_learner_prompt`, `_run_predictor_via_sdk`, `run_predictor_via_sdk`, `_run_learner_via_sdk`; predictor skill path const `_PREDICTOR_SKILL_PATH`. The `_via_sdk` callsites are existing-code anchors to replace, not target transport names.
- Prior-report / lesson-era rewrite points: `earnings_orchestrator.py` — `_decorate_with_learner_paths`, `build_learning_context`, `append_ticker_lesson`, `append_global_lessons`, `aggregate_lesson_audits`, `_validate_audit_against_prediction`.
- Lesson-era teardown list is not exhaustive: implementation must grep `scripts/earnings` + relevant skills for lesson-era symbols/strings (`lesson`, `lessons`, `learnings`, `lesson_audit`, `predictor_lessons`, `data_lessons`, `global_observations`, `#S10.lesson`, `_allowed_learner_paths`, `learner_result:`) and remove/rewrite all matches to §6/§8/§11/§12 targets; do not preserve hidden lesson lifecycle surfaces.
- Migration safety gates: (1) byte-identical pre/post snapshot of builder + renderer outputs — sections marked unchanged in this design must produce identical bytes; (2) scoped grep for lesson-era surfaces (the teardown list above) — must return zero matches. Stop-on-red; never weaken assertions to make tests pass.
- Predictor SKILL frontmatter: DELETE only the static `allowed-tools` block from `.claude/skills/earnings-prediction/SKILL.md`; keep fork-relevant frontmatter such as `context: fork` and `permissionMode: dontAsk` for historical slash-skill invocation. Live predictor embed (§1.2.3) must load the SKILL body with YAML frontmatter stripped — mirror the existing learner pattern in `earnings_orchestrator.py::_load_learner_skill_content()`, which already strips frontmatter at load time. Tool gating remains: historical = §1.1.2 PreToolUse hook (runner-enforced); live = prompt-level guidance per §1.2.2.1 + time-SLA per §1.2.1 (no runner-enforced allowlist for live).
- Learner validator: `scripts/earnings/validate_learning.py` — rewrite from lesson lifecycle schema to `learner_result.v1`.
- Renderer: `scripts/earnings/renderer/bundle.py` and `scripts/earnings/renderer/lessons.py` — replace lesson Section 10 with prior learner reports.
- Context builders: `scripts/earnings/builders/adapters.py` and existing builders under `scripts/earnings/builders/`; keep builder layer, add prior reports after builders per §11.
- Skills: `.claude/skills/earnings-prediction/SKILL.md` and `.claude/skills/earnings-learner/SKILL.md`.
- Result markdown: `scripts/earnings/result_md_renderer.py`.
- Guidance extraction pipeline (separate from the `guidance_history` bundle builder): `scripts/extraction_worker.py` (SDK/`claude -p` entrypoint = the interactive-TMUX change point), `scripts/guidance_trigger_daemon.py` (trigger), `scripts/harvest_guidance_sessions.py` (harvest), `.claude/skills/guidance-inventory` (extraction contract). Transport-only per §4; preserve prompts/outputs/validators.
- TMUX/subscription transport implementation anchors live in `.claude/plans/tmux-transport-handoff.md`; do not duplicate them here.
- EV1 scorer: `scripts/earnings/scoring/ev1.py` (new module). Inputs: `prediction/result.json` + `learning/result.json::actual_return_pct`. Outputs: per-event `scoring/result.json` (under `earnings-analysis/Companies/<T>/events/<Q>/`) + rolling `earnings-analysis/scoring/ev1_aggregate.json`.

# 18. Prediction Scoring
- This is the EV1 scorer: deterministic code over `prediction/result.json` + actual report-window return; the LLM never authors graded numbers.
- Actual return source is the orchestrator-stamped report-time reaction return (§8 `actual_return_pct`; currently derived from Neo4j `PRIMARY_FILER.daily_stock` via `fetch_actual_return` / `normalize_actual_return`), not trade P&L.
- Direction score: compute `direction_correct` from predicted direction vs signed actual return.
- `actual_direction` is derived from `actual_return_pct`: `long` if >0, `short` if <0, `flat` if =0. Derived, not stored in result.json schemas; rendered into §6 prior_report_row by the orchestrator.
- `direction_correct` is `null` when `direction == no_call`; otherwise `direction_correct = (direction == actual_direction)`.
- Magnitude score: signed predicted midpoint = sign(direction) * midpoint(`expected_move_range_pct`); compare to signed actual return for signed error and MSE.
- Calibration: compute Brier/calibration from raw `confidence_score` vs `direction_correct`.
- Buckets are grouping/display only; all math uses raw values, never bucket labels.
- Aggregates: hit rate by direction, mean signed error/bias, MSE, Brier, calibration by bucket, ticker, quarter, and replay suite.
- `no_call` is tracked separately from directional calls; do not mix operational timeouts with reasoned no_call.
- Live timeout / killed / missing-result runs are excluded from accuracy/calibration/MSE/Brier by default and reported as operational health.
- Trade P&L / executioner outcomes are downstream execution analytics only; do not add realized_trade_return_pct or trade P&L to prediction_result.v1, learner_result.v1, prior reports, Section 10, key_takeaway, future_checklist, predictor bundles, or scoring inputs.
- Earnings artifacts may feed a future executioner; executioner outcomes never flow back into predictor-readable context or learner inputs.
- Use a frozen representative + edge replay set; do not re-pick the set after seeing results.
- Learner may read scorer-owned results when rendered in prior-report rows, but never authors them.
- EV1 scorer module location: `scripts/earnings/scoring/ev1.py` (new). Runs deterministically per event, triggered just after `learning/complete.json` is written (analogous to learner's just-in-time trigger per §22).
- EV1 artifacts: per-event score at `earnings-analysis/Companies/<T>/events/<Q>/scoring/result.json`; rolling aggregate at `earnings-analysis/scoring/ev1_aggregate.json`, recomputed deterministically from per-event scores. Scoring writes are atomic and overwrite-safe; outputs are code-owned, never LLM-authored.
- EV1 idempotency: per-event scoring is a pure function of `prediction/result.json` + `learning/result.json::actual_return_pct` + scorer version/config. Re-running on the same inputs produces byte-identical output. If `actual_return_pct` is later corrected upstream (data revision), the scorer recomputes — overwrites are safe.

# 19. Artifact Contract
- Event root contains `context_bundle.json` and `context_bundle_rendered.txt`.
- Prediction artifacts live under `prediction/`: `result.json`, `result.md`, `section_audit.json`, optional `reasoning.md`.
- Learner artifacts live under `learning/`: `result.json`, `result.md`, optional `reasoning.md`.
- `prediction/result.json` schema stays `prediction_result.v1`.
- `learning/result.json` schema becomes `learner_result.v1`; reconcile all stale `attribution_result.v2/v3` strings to this target.
- Delete/stop writing lesson stores: `earnings-analysis/learnings/ticker/*.json`, `earnings-analysis/learnings/global.json`, global locks, ticker/global lesson appends, and lesson audit aggregation.
- `experiments/` (baseline `prediction_no_lessons` runs) is obsolete with lessons removed: stop writing it; existing dirs may be left in place, never read for machine state.
- Existing valid target-schema `learning/result.json` is sufficient for learner recovery (post-cutover ongoing ops; §23 wipe is one-time migration); no derived lesson writes are required.
- `result.md` is renderer output from `result.json`; code never parses markdown for machine state.
- Learner `result.md` heading order: `## Header` · `## Actual Returns` · `## Primary Driver` · `## Contributing Factors` · `## Feedback` · `## Key Takeaway` · `## Future Checklist` · `## Evidence Ledger`. All 8 sections always present. Render `missing_inputs[]` under Feedback and `data_sources_used[]` under Evidence Ledger; learner `result.md` has no Section Audit.
- Scoring artifacts: per-event `scoring/result.json` (EV1 score, deterministic + overwrite-safe); rolling aggregate at `earnings-analysis/scoring/ev1_aggregate.json` (deterministically recomputable from per-event scoring files).

# 20. Peer-Earnings Window (D4)
- For peer earnings snapshot, use this ticker's previous Item 2.02 8-K timestamp (`quarter_info.prev_8k_ts`) as `window_start`, ending at predictor `pit_cutoff`. If `prev_8k_ts` is missing, keep the existing 45d fallback.
- Implementation target: in `scripts/earnings/builders/adapters.py::build_peer_earnings_snapshot`, pass `window_start=quarter_info.get("prev_8k_ts")` into `scripts/earnings/builders/peer_earnings_snapshot.py`; keep the existing query, same-industry peer universe, mkt-cap ranking, self-exclusion, Item 2.02 filter, and `< pit_cutoff` PIT gate. Adapter passes `prev_8k_ts` or `None` verbatim; `build_peer_earnings_snapshot` owns the 45d fallback.
- Do not widen to sector/size-band except the bounded ≤2-company fallback explicitly approved in §21; do not add adaptive window/N knobs, use most-recent-ever peers, or change §6 peer learner reports under D4.
- Residual peer-starved (≤2-company) industries: the deterministic PIT-safe size-band/sector fallback is USER-approved per §21 (bounded ≤2 exception only; not general widening).

# 21. Deferred Items — Notes for Implementation Bot
- D13 (live evidence grounding): the SRC:LIVE runtime catalog is deferred, not dropped. Design a minimal, reliable way to register/attest live-fetched facts so live `key_drivers[].evidence[]` and `evidence_ledger[]` IDs resolve — WITHOUT restricting what live-mode prediction may fetch. Grounding records provenance; it must never become an access gate. Until built, live grounding is weaker per §10.
- D4 (peer-starved industries): when the same-industry peer universe has ≤2 companies, §20 peer-earnings snapshot uses a deterministic, PIT-safe size-band/sector fallback (USER-APPROVED) — bounded ≤2 exception only; NOT applied to §6 peer learner reports (which follow §6's "show fewer" rule). The primary path stays same-industry, mkt-cap-ranked. Never LLM-selected.
- D21 (skill eval): before production, remind the USER to run the official Anthropic skill-plugin eval on all skills — especially predictor and learner — to verify they are correct/complete. Implementation/QA gate, not a design item.
- Post-stabilization artifact/Obsidian cleanup: after predictor/learner/orchestrator are coded and tested, and before EarningsTrigger production activation, revisit the §23 KEEP list plus Obsidian vault layout; these paths are not permanent architecture.
- Sector/macro DataSubAgents (deferred): future tracked task, out of current scope. When built: live IBKR / historical Polygon(+Yahoo), PIT-safe per `.claude/plans/DataSubAgents.md`, same envelope, on-demand by predictor(live)/learner(any). PIT audit still applies before any historical-mode use; not obviated by the historical predictor's DataSubAgent removal.

# 22. Execution Architecture (Trigger / Daemon / Worker)
- **Implementation timing (READ FIRST):** wire/test predictor, learner, and orchestrator before building §22 trigger/daemon/worker. Use `.claude/plans/EarningsTrigger.md` as the trigger-layer source, adapted to TMUX transport (§5) and the new `prior_reports_context` / `learner_result.v1` artifacts; scrub lesson-era vocabulary and revalidate details before implementation.
- **Topology:** Separate `earnings-trigger` daemon (long-running) → Redis `earnings:pipeline` list (with leases) → thin `earnings-worker` that BRPOPs and invokes `earnings_orchestrator.py` per job. Worker owns nothing semantic; the orchestrator owns bundle/prediction/learner dispatch via TMUX transport (§5).
- **Completion truth:** a component is complete only when BOTH its `result.json` validates AND its `complete.json` sentinel exists. `result.json` alone is not completion truth under retries; sentinel alone is not completion truth because it would mask a missing/corrupt `result.json`. Sentinel scope = prediction + learning ONLY; guidance completion truth lives in Neo4j `guidance_status='completed'`.
- **Mode-asymmetric guidance gate:** Historical prediction is hard-gated on same-quarter Neo4j `guidance_status='completed'` before bundle assembly; missing → log `WAIT_GUIDANCE`, do not enqueue. Live prediction is NOT gated; missing guidance surfaces as a `data_gaps[]` entry and the predictor continues with the degraded bundle. Prior-chain completion gates still apply where applicable; brand-new live tickers are not forced through silent historical backfill before their first live prediction.
- **Warm-start anchor:** For each ticker, the earliest earnings 8-K whose `filed_8k` timestamp has at least one usable PIT-visible **prior 10-Q or 10-K** (a prior periodic financial baseline — not a prior 8-K). Quarters before the anchor are pre-history; skip, not "missing chain work." If no anchor exists for a ticker, trigger emits `SKIP no_warm_start_anchor` and does not enqueue. Definition follows `EarningsTrigger.md` "Warm-start anchor (locked requirement)" — do not re-derive.
- **Learner trigger:** Just-in-time before the next prediction for that ticker; NO scheduled cron. If a new prediction is about to start AND no learner ran since the prior outcome became knowable, the trigger fires the learner first.
- **EV1 scorer trigger:** fires just after `learning/complete.json` sentinel is written (per-event); scorer reads `prediction/result.json` + `learning/result.json`, writes per-event `scoring/result.json` + refreshes `earnings-analysis/scoring/ev1_aggregate.json`. Re-runnable without side effects.
- **Retry/recovery invariants:** Worker retries must not corrupt Neo4j `guidance_status`, the run-ledger, or `prediction/learning` sentinels; sentinel writes are atomic and idempotent.

# 23. Cutover Wipe
- At cutover only (irreversible, last migration step): WIPE all per-event artifacts — `context_bundle.json`, `context_bundle_rendered.txt`, `related_filings/`, `prediction/`, `learning/` — and legacy lesson stores `earnings-analysis/learnings/ticker/*.json`, `earnings-analysis/learnings/global.json`, `earnings-analysis/learnings/global.lock`.
- KEEP across cutover: `earnings-analysis/predictions.csv`, `earnings-analysis/prediction_processed.csv`, `earnings-analysis/thinking/`, Obsidian skeleton, and `earnings-analysis/Companies/<T>/events/<Q>/` directory skeletons.
- Wipe granularity: delete files/subdirs inside each per-event directory (`prediction/*`, `learning/*`, etc.); do NOT delete preserved per-event directory shells.
- Tar-insurance before any WIPE; preservation assertions on the KEEP list are the gate; failure of any assertion aborts the wipe.
