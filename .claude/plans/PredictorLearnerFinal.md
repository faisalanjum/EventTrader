
# Final Plan
Plan is to completely revert to the simplest possible versions of Prediction & Learner & earnings_orchestrator.py 

Overarching principle is to rely on free form text and let the entire process of learning and prediction be completely informal but well organized so predictor can access them on demand.

> **Supersession note (2026-05-12).** The Refinements sections below supersede the earlier rough wording in this doc. Where the top-of-doc text says "absolutely nothing on provenance," "yaml frontmatter," "no restriction on # of links," or similar — read the numbered refinements as authoritative.

---

## Predictor

1. Same as today makes a prediction but inspite of getting lessons (with elaborate lifecycle management & all its contexnt and auditability etc fields), instead predictor only gets a couple lines of summary per each previous learning as well as a link to previous learner reports - note these are not lessons anymore but a short summary + links which if it opens has learner reports in free-form text. No restriction on proving # of previous links. No audit history, no lesson grading, no watch no misled etc etc, no provenance, no lesson, no lesson lifecycle managemnt - absolutely nothing.

2. The summary generated will be by learner itself inside the same report and we need a super simplistic way of making earnings_orchestrator fetch it - one idea is maybe yaml frontmatter of something stupidly simple so for example earnings_orchestrator is probably already injecting previous learner links - in addition, it can have a python line or 2 which essentially just picks up this summary from the yaml frontmatter written by Learner after each prediction report (note yaml frontmatter is just a silly suggestion to make things extremely simple but think if there is an even easier way)

3. So far predictor was restricted in terms of being able to access data outside (present in its context bundle + read command) - I am considering allowing it to access any data available in our db + even web. One beneift of this approach is we can continue to use same skill for both historical + live mode as explained below. However, 2 Issues which we will have to deal with:

   3.1: Speed - In addition to accuracy, Prediction's effectiveness depends on how fast can it take decisions. Based on this we had earlier restricted it (or atleast designed the skill) so that it won't make any elaborate inquiries outside of its context bundle except for maybe being able to read md files on disk. One clear disadvantage was it in few cases may not have all the information it needed even though this meant it can come up with final prediction super quickly. Now planning to give it access to mcp, IBKR Live data (still need to buy the subscription) as well as Webfetch and other tools but we will ensure its made aware of time_since_release so it doesn't take forever (maybe inject this variable every 30 seconds or may be find another better much simpler approach)

   3.2: The second reason we did not let it make consequent turn tool calls was to do with PIT. To be clear, PIT is only useful for making predictions for historical (already released) reports which in turn served to prove how effective this system is in addition to seeding the system with learnings before it actually starts prediction in real-time. For this we have .claude/plans/DataSubAgents.md which do solve this issue for the most part but (in rare data sources it may not be completely reliable which is fine). In anycase I will be testing this restriction seperately but need to keep a note. But most importantly, Live real-time prediction has absolutely 0 restriction in terms of what it can access other than "it should be quick" since people who place their orders first get a better bargain.

4. Maybe: We may create a seperate sector (& or macro) agents whos task is fetch whats current situation of the sector/macro but this can be one of the last things we build if at all. Also given this, predictor and or learner may be for example be able to pull copper prices for a certain day and so on. just a silly example.

5. Finally in addition to providing links to previous quarter learner reports (I think earnings_orchestrator.py already puts it in the context bundle), we can also put links for other companies in the same sector and over the last few months. Note the dates and sector and company names are already claculated by the earnings_orchestrator.py and put in context bundle so incremental work is relatively simple.

6. TBD: Not sure if its worth asking predictor to output exact predicted return so in historical backtesting (& may be for learner's ease) we can compare mean squared effor between predicted and actual. But again the overarching principle is do not include if it doesn;t materially increase our primary goal of making correct & timely predictions.

7. We also need to understand if there are some better thoughts inside the latest created plan (.claude/plans/LearnerLoopPlans/LearnerLoopPlan_LessonIntelligence_Minimal.md) (which by the way no longer applies wholistically) but it may be worth seeing if it has some good considerations - this is just one of them so ensure you look at if there is any other good considerations we could borro but ensure its applicable and even then the most we would borrow is a most simplistic version of it. One example (again your task is to look for all possible ones) is that the tug between confidence and prediction and how Brier score was used but not sure if its at all applicable so check?

8. Also note in earlier setup we had scope for cross tickers and sector and macro and so on - the way we will be managing that is for sector and macro have these data agents which on demand will fetch the required data. For cross company - we will be including links to previous learner reports so if predictor wanted it could read it on its own - finally we will guide the predictor using the workflow steps so it doesn't go over board.

---

## Learner

1. Completely get rid of lessons in totality and all its fields and orchestration and auditability and every thing.

2. Learner's task is simply to figure out if prediction was off and why was it off and what were the main drivers which led to a different outcome - we can keep evolving its skill as to the exact detals but taht can be a living document.

3. In addition, the data gaps it will report are only for what data it has access to but the predictor did not happen to use them. Its not for what potentially could have been useful but only sort-of a guide for predictor that it could have used the data already available.

4. Augment the Learner with Sector & Macro context sub agents so that when figuring out what happened it can have entire context which will be useful for the predictor.

### Disadvantages

1. This can cause context bloat since we are allowing predictor to access free form text in the shape of previous learner reports but the alternative of managed lessons is unwiedly for me to understand and manage. Moreover, I feel free form text is better for LLM context to make better decisions provided we guide the workflow steps in predictor and learner skills appropriately but open to challenges.

---

The final task will be to super throughly understand what has already been coded and compare it to the above super minimalistic desgn and then need to understand how to take current code to the target state and in the process ensuring all of the complexity we created in codebase is 100% completely removed, leaving a super coherent and maximally minimalistic codebase for this specific module/files.

As a note I will be wiping all previous prediction files and starting over so no need to worry about backward compatibility.

---

## Refinements (2026-05-12)

Each item tagged [ALREADY] = already in code, [PARTIAL] = partially in code, [NEW] = net-new work.

1. **[NEW] Anti-lazy in prompt + validator.** Q1 FCX-style lazy directional calls are prevented by BOTH an explicit predictor workflow step and a validator hard-block requiring ≥2 grounded source IDs for any directional (`long`/`short`) call, with ≥1 source ID from the current bundle per V2. Current predictor-skill grounding exists through `evidence_ledger[].source_id` and the non-lesson key-driver rule (`.claude/skills/earnings-prediction/SKILL.md:232`), but there is no explicit ≥2 directional anti-lazy rule in the prompt or validator. Earlier "prompt-only" wording is superseded by V1/V2 below.

2. **[PARTIAL] `expected_move_range_pct` midpoint is available; MSE is target work.** The current predictor already emits `[low, high]` at `.claude/skills/earnings-prediction/SKILL.md:195`, and `finalize_prediction_result` derives `magnitude_bucket` from the range midpoint. No current backtest/evaluation MSE implementation was found in `scripts/`; EV1 below defines the target metric as signed-midpoint MSE.

3. **[PARTIAL] Locked summary fields in `learning/result.json`.** Two NEW fields to add: `key_takeaway` (1 sentence) + `future_checklist[]` (things to check next time). Tags were considered and DROPPED (FIX-8 — no consumer). Orchestrator reads these from the JSON file directly (not from `.md`) for discovery, PIT filtering, caps, and the summary shown to the next predictor; the predictor then reads the rendered bundle and opens allowlisted `learning/result.md` reports for full prose. Current learner already emits `primary_driver` + `feedback{what_worked, what_failed}`.

4. **[NEW] Speed via injection + tiered SLA (LIVE only).** Inject `time_since_release` every turn (or one-shot at kickoff + enforce hard timeout) so predictor sees elapsed time. **Live SLA (per FIX-10):** 90s soft warn / 120s ship-the-call / 300s hard kill. Historical mode keeps a softer budget with no hard kill.

5. **[PARTIAL] Mode-aware tool gating, single skill.** One skill with `pit_mode={historical, live}`; historical exposes DataSubAgents only (PIT-safe), live exposes full tools (web, neo4j, IBKR, MCP). Avoids two divergent skill files. Current: `pit_mode` field already exists in learner output (`historical`/`live`); skill does not yet gate tools by mode — add gating.

6. **[ALREADY] No learner-AUTHORED YAML; renderer metadata frontmatter OK.** Learner writes `learning/result.json` only — no YAML hand-authored anywhere. The `.md` file's existing autogenerated frontmatter (`autogenerated: true`, `source: result.json`, `generator: ...`) is renderer metadata and stays. Orchestrator never parses `.md` for machine state; predictor may read allowlisted rendered `.md` reports for reasoning.

7. **[NEW] Wipe FCX corpus.** Stale, file inconsistencies, only Q3 usable; regeneration under new design is cheaper than preservation.

8. **[NEW] Sector/macro sub-agents deferred.** Copy the existing DataSubAgents pattern when the first prediction proves the need; not a blocker for shipping the new predictor/learner.

9. **[NEW] Historical + live ship together.** Both modes ship in the same release; mode flag gates tools, skill workflow is shared. Do not stage live for later.

10. **[ALREADY] Keep `evidence_source_catalog`.** `SRC:TICKER:QUARTER:ACCESSION#location` IDs in `key_drivers[].evidence` ground every cited fact at `.claude/skills/earnings-prediction/SKILL.md:203`, independent of lessons. Citation grounding survives the lesson removal.

11. **[NEW] Context bloat ignored on cost grounds.** Claude Code Max absorbs the dollar cost; cost is not a reason to cap report count. Attention quality IS a reason to cap (see #19).

12. **[ALREADY] `learning/result.json` is the only structured surface.** Confirms #6 from a different angle: the JSON file is the canonical structured artifact; `learning/result.md` is the canonical LLM reading surface auto-rendered from it (with minimal autogen frontmatter as renderer metadata only). Nothing else is structured anywhere in the report.

13. **[PARTIAL] Tiered reading discipline for linked reports (per FIX-7).** Skill enforces: (1) MUST fully open the most-recent 4 own-ticker reports. (2) Older own-ticker reports (positions 5–8) are summary-first; open only if takeaway/setup suggests relevance. (3) May open up to 3 of the 4 visible peer reports based on summary. (4) Must record opened reports in JSON (`opened_prior_reports[]` per S1). Current code: predictor skill Phase 1-4 workflow + `learner_result:` link allowlist exist, but reading is OPTIONAL today — make tiered reading the contract.

---

## Borrowed from ChatGPT review (2026-05-12)

14. **[NEW] Anti-lazy applies to ALL directional calls, no confidence threshold.** Q1 FCX was confidence 48 with direction `short` and still lazy — any threshold (≥60) would have missed it. Rule: `direction in {long, short}` requires ≥2 grounded source IDs regardless of confidence, with ≥1 source ID from the current bundle per V2. Same scope as #1.

15. **[ALREADY] Preserve existing JSON-canonical, .md-rendered pattern.** Already in code: learner writes `learning/result.json`; `scripts/earnings/result_md_renderer.py` produces `learning/result.md` from it. Keep this pattern in the new design — Python/orchestrator parses JSON directly and never parses `.md` for state, while the predictor reads the rendered bundle first and opens allowlisted `learning/result.md` reports for full prose. ChatGPT framed this as a borrowed idea but it's the current pattern; just don't accidentally regress to markdown-with-embedded-JSON.

16. **[ALREADY] Richer learner JSON schema.** Current learner schema is already RICHER than ChatGPT proposed: `primary_driver`, `contributing_factors`, `feedback{what_worked, what_failed}`, `global_observations`, `missing_inputs`, `evidence_ledger`, `lesson_audit`. Keep this surface; just drop `lesson_audit` (lessons gone) and consider adding `future_checklist[]` for the next predictor (see #20 for naming).

17. **[NEW] Tiered SLA for LIVE mode only (per FIX-10).** Live SLA: 90s soft warn (warning injected) / 120s operating target (predictor MUST ship best-available call unless actively resolving material uncertainty) / 300s hard kill (orchestrator force-terminates; writes timeout no_call fallback). Historical mode keeps soft cap with no hard kill.

---

## Second-round borrows from ChatGPT review (2026-05-12)

18. **[NEW] Signed midpoint for MSE.** Current `expected_move_range_pct` is positive-only; for the new evaluation metric compute signed = sign(direction) × midpoint(range), then compare to signed actual_pct. No current MSE/Brier implementation was found in `scripts/`; this refines item #2 as target work.

19. **[NEW] Cap prior-report count for attention quality (per FIX-7).** Cap at **12 visible prior reports** per prediction: 8 own-ticker + 4 industry-peer. Forced-open only the most-recent 4 own-ticker; older are summary-first. May open up to 3 peers based on relevance. Refines item #11.

20. **[NEW] Rename "what_to_check_next_time" → "future_checklist".** Shorter, clearer, implies the field gets used as an actual checklist by the next predictor. Refines items #3 and #16.

21. **[NEW] Predictor selects optional linked reports to open after forced own-ticker opens.** Two-pass: first see linked-report metadata (date, ticker, 1-line summary), then MUST fully open the most-recent 4 own-ticker reports and may select older own-ticker / peer reports to open fully under FIX-7 caps. Avoids forced reading of irrelevant older/peer reports. Refines item #13.

22. **[NEW] Keep evidence catalog STRICT; broaden it.** Reject ChatGPT's "optional/selective" suggestion — drift risk. Instead extend `evidence_source_catalog` to cover sector/macro agents and web/IBKR in live mode, keeping the strict `SRC:` format.

---

## Hard Prerequisites Before Implementation

- **Lock the exact `result.json` shape for prediction and learner BEFORE writing any code.** Full field list, types, and required-vs-optional status must be finalized. Decide the `result.md` rendering template (which fields become headings, which become bulleted lists, ordering, etc.). Starting point: merge items #3 and #16 into one schema. This is not optional — coding without locked schemas guarantees rework.

---

## Current Code -> Target Code Change Map

- **Keep the bundle substrate; replace only memory.** Keep 8-K/results/guidance/consensus/financials/inter-quarter/peers/macro/PIT builders; replace `learning_context` with `prior_reports_context`.
- **Replace Section 10 renderer.** Retire `renderer/lessons.py` and `_render_learning_context`; add a tiny prior-report renderer showing per-report bullet (Date / Ticker / Quarter / predicted vs actual / key_takeaway / link) per O2 + P4 (tags dropped per FIX-8).
- **Keep `evidence_source_catalog`; rewrite S10 anchors.** Remove `#S10.lesson.Ln`; add `#S10.report.Rn` / agent/web/live anchors so all cited facts remain validator-grounded.
- **Remove lesson stores.** Delete/ignore `earnings-analysis/learnings/*`, `get_learnings_paths`, `append_ticker_lesson`, `append_global_lessons`, lesson IDs, locks, lifecycle state, and audit history.
- **Simplify learner recovery.** Existing valid `learning/result.json` means recovered; no derived lesson writes, no global/ticker append recovery, no audit aggregation.
- **Delete lesson audit machinery.** Remove `aggregate_lesson_audits`, `_validate_audit_against_prediction`, `lesson_audit`, `lesson_labels` count matching, and `cites_lesson_indices`.
- **Simplify prediction validator.** Keep schema/metadata/range/evidence-source validation; remove formal lesson-label validation; add the directional anti-lazy hard-block: `long`/`short` needs ≥2 grounded source IDs across key drivers, with ≥1 from the current bundle per V2. Live mode also accepts validator-approved `SRC:LIVE:*` runtime IDs per V3/V4.
- **Simplify learner validator.** Keep actual return, evidence ledger, primary/contributing drivers, prediction comparison, missing inputs, data sources, refs; remove structured lesson/global-observation routing rules.
- **Make `learning/result.json` the only machine/source-of-truth memory.** Add `key_takeaway` (1 sentence) + `future_checklist[]`. Tags considered and DROPPED (FIX-8 — no consumer). Orchestrator scans prior event `learning/result.json` files and renders links/summaries for the next predictor; each included report must carry an allowlisted `learning/result.md` path for predictor reading. If `result.md` is missing, regenerate it from `result.json`; do not parse markdown as source truth.
- **Update both skills.** Prediction skill removes formal lesson review and uses two-pass prior-report selection; learner skill removes lesson authoring/auditing and writes causal report JSON plus future checklist.
- **Update markdown renderer.** `result_md_renderer.py` should render the new learner report fields and stop rendering predictor lessons/global observations/lesson audits.
- **Mode-aware tools are runtime config.** Historical exposes DataSubAgents-only PIT-safe access; live exposes broader web/Neo4j/IBKR/MCP access with hard live timeout/tool budget.
- **Rewrite scripts/tests around the new memory surface.** A/B scripts become `with_prior_reports` vs `without_prior_reports`; golden renders and validator tests must replace lesson expectations with prior-report expectations.
- **Delete lesson-specific tests; keep substrate tests.** Remove tests for lesson rendering, lifecycle, ID stability, audit aggregation, and lesson cross-file validation; keep bundle builders, PIT, evidence catalog, result rendering, validators, and loop smoke tests.
- **Expected work size.** Medium rewrite: production logic is mostly removal + one small prior-report builder; main cost is test/golden churn and prompt/schema cleanup.

---

## Additional Specifics Verified Against Code (2026-05-12)

These augment the change map above with precise file/function/line evidence. ChatGPT's map is shape-correct; these are the surgical specifics.

- **`prediction_no_lessons` baseline experiment ALREADY exists in code.** `result_md_renderer.py:502` `render_baseline_experiment`, `_prediction_body(..., is_experiment=True)` at line 120, `thinking_harvester.py` validates the experiment name, locked by `.claude/plans/obsidian_thinking.md`. **Reuse the experiment/render/harvest scaffolding** — but note the new default is `prior_reports`, not zero-context. The baseline's "no_lessons" predictor behavior is NOT the target.
- **`_allowed_learner_paths` IS the existing PIT-safe prior-report FILE allowlist.** Defined at `orchestrator.py:2093`, consumed at `renderer/lessons.py:195`, invariant-checked at `orchestrator.py:1709-1758`. Rename to `_allowed_prior_report_paths` and reuse for the prior-report `.md` file allowlist. NOTE: this mechanism only covers file-path allowlisting; it does NOT solve live web/IBKR/Neo4j/MCP tool gating, which needs a separate runtime `pit_mode` / tool-profile config (see item #5).
- **Delete `_text_utils.py` (79 lines), but only AFTER removing all callsites.** Contains `_normalize_lesson_text` and `iter_labeled_lessons`. Imports to drop: `orchestrator.py:337, 641, 2817, 3003`. CRITICAL — `_normalize_lesson_text` is also CALLED in 10 expressions across these line refs inside orchestrator.py: 790, 830, 834 (inside `validate_prediction_result`), 1846, 1847 (inside `_content_matches`), 2846, 2847 (inside `aggregate_lesson_audits`), 3043, 3044 (inside `_validate_audit_against_prediction`). The 6 call expressions at 1846–3044 disappear when their containing functions are deleted; the 4 call expressions at 790/830/834 must be removed as part of the `validate_prediction_result` simplification (see Validator preservation item below). `validate_learning.py` has zero `_text_utils` refs.
- **`renderer/__init__.py` cleanup.** Remove `from .lessons import _render_learning_context` (line 36) and the matching entry in `__all__` (line 50). Add export for new `_render_prior_reports`.
- **20 orchestrator functions to REMOVE outright between lines 1463–2767 (~1200 lines).** `_stamp_ticker_lesson_row` (1463), `append_ticker_lesson` (1487), `append_global_lessons` (1563), `_assert_learner_paths_invariant` (1700) — replace with a smaller prior-report invariant check, `DuplicateLessonIdError` (1776), `_routing_key_from_source` (1790), `compute_lesson_id` (1817), `_content_matches` (1840), `assert_no_id_collision` (1862), `compute_status` (1900), `_passes_audit_pit` (1961), `_apply_render_view` (1986), `_stamp_quarter_row_skeleton` (2445), `_upsert_audit_in_history` (2473), `_apply_audit_ticker` (2491), `_apply_audit_global` (2533), `_apply_audit_and_append_global_atomic` (2565), `_append_lesson_row_to_ticker_quarter` (2614), `_register_replacement` (2670), `aggregate_lesson_audits` (2767). PLUS `_validate_audit_against_prediction` (line 2968) — also lesson-bound (asserts `lesson_audit` count == `lesson_labels` count, imports `iter_labeled_lessons`) and called from `run_learner_for_quarter` at 1261 (1248 is only a comment) and `_full_validate_for_orchestrator` at 3098. DELETE it AND its two real callsites.
- **REWRITE not delete: `build_learning_context` (2101) → `build_prior_reports_context`.** Replace lesson-loading body with prior-report selection; reuse PIT-filter logic and `_allowed_learner_paths` plumbing.
- **REWRITE not delete: `_decorate_with_learner_paths` (2030).** Keep the current-quarter PIT self-guard (2064–2067; 2055–2060 is only the idempotency `.pop()` prelude) and allowlist assembly (Phase 2); change per-entry attachment from lessons to prior-report summary rows.
- **Hook `validate_learning_output.py` (`.claude/hooks/`) STAYS.** Wrapper logic untouched; the imported `validate_attribution_result` function name is preserved across the rewrite. Path-matcher (`endswith("/learning/result.json")`) is correct.
- **Schema-version naming + write sites.** S3 locks the target names as `prediction_result.v1` (keep) + `learner_result.v1` (rename/reset). Current code is not internally uniform: `validate_learning.py:133,135` and `.claude/skills/earnings-learner/SKILL.md:40,46` use `attribution_result.v3`, while stale renderer/orchestrator docstrings still mention `attribution_result.v2` (`result_md_renderer.py:218,483`, `earnings_orchestrator.py:893`). Reconcile all attribution-result strings into `learner_result.v1` during the rewrite. For prediction, `orchestrator.py:701` is the validator check and `3510` is the schema write; keep the schema name per S3 while adding/removing fields and validator rules. `result_md_renderer.py:121` is the prediction-result docstring. `ticker_lessons.v2` / `global_lessons.v2` constants delete with their files. ALSO update: `.claude/skills/earnings-learner/SKILL.md` (carries learner schema strings), `scripts/earnings/tests/fixtures/learner_session.jsonl` (fixture contains learner schema_version), prediction skill output example/field definitions (no schema string there), renderer-docstring references, validator error messages that name schema strings, and frozen test JSON fixtures.
- **Quantified churn (ESTIMATES — confirm per-file during implementation).** Orchestrator: ~1200 lines removed (out of 4063); `grep -ci lesson scripts/earnings/earnings_orchestrator.py` returned 383 on 2026-05-15. `validate_learning.py`: rewrite (616 → ~200 lines). `renderer/lessons.py` + `_text_utils.py`: delete (377 lines). **Tests/helpers:** 2026-05-15 grep found 29 lesson-touching Python/helper files; exact delete vs rewrite split still needs per-file triage. **Goldens/fixtures:** 2026-05-15 content grep found 29 lesson-touching fixture/golden files; direct lesson-render golden paths are 9 (8 under `golden_renders/sections/lessons/` plus `golden_renders/degraded/no_lessons.txt`). Enumerate again from fresh grep/find before editing in case fixtures changed.
- **Predictor SKILL.md surgical map.** Delete §3.3 (lines 81–135) entirely. Strip `lesson_labels`, `cites_lesson_indices` from §5 example + field defs. Delete line 114 (Citation rule), line 116 (analysis substring rule), line 197 (cites_lesson_indices in key_drivers def), line 232 ("lessons inform interpretation"). Rewrite lines 27–31 (replace `S10.lesson.L<n>` source-ID pattern with `S10.report.R<n>`).
- **Learner SKILL.md surgical map.** Delete §Structured lesson output v3 (82–125), §Lesson audit v3 (126–186), §Global observations (191–263), §Phase 4 Distill Lessons (306–322). Rewrite §Feedback block table (63–73) to drop predictor_lessons/data_lessons rows. Add `key_takeaway` (1 sentence) + `future_checklist[]`. Tags dropped per FIX-8.
- **Predictor/learner prompt builders.** `_build_predictor_prompt` (`orchestrator.py:3599`): **no lesson logic inside this function** — verified it only passes path env vars (`BUNDLE_PATH`, `RENDERED_BUNDLE_PATH`, `SECTION_AUDIT_PATH`, `RESULT_PATH`). The lesson surface that flows to the predictor lives in the rendered bundle (`renderer/lessons.py` output) + the predictor SKILL.md prompt itself; removing those upstream surfaces is sufficient. `_build_learner_prompt` (`orchestrator.py:3118`): strip `PRIOR_LESSONS` and lesson-section instructions from the runtime prompt. `_load_learner_skill_content` (`orchestrator.py:3107`): no code change beyond reading the rewritten learner SKILL.md.
- **Builders directory is CLEAN (verified).** Zero lesson references across all 8 builder files (`adapters.py`, `consensus.py`, `eight_k_packet.py`, `guidance_history.py`, `inter_quarter_context.py`, `macro_snapshot.py`, `peer_earnings_snapshot.py`, `prior_financials.py`). No changes needed.
- **Non-lesson renderer files CLEAN (verified).** Zero lesson references in `consensus.py`, `financials.py`, `_formatters.py`, `guidance.py`, `header.py`, `inter_quarter.py`, `macro.py`, `peers.py`, `results.py`. Only `bundle.py` (4 refs) and `__init__.py` (2 refs) need edits.
- **`run_ledger.py` CLEAN (verified).** Zero lesson references. Unchanged.
- **`_atomic_write_json` (`orchestrator.py:1444`) STAYS.** Used by prediction finalize + result.json writes outside the lesson surface.
- **Validator preservation.** `validate_prediction_result` (`orchestrator.py:658`): KEEP U67 `evidence_source_catalog` grounding (lines 853+) — that's the citation anchor that survives. REMOVE: (a) `lesson_labels` from the local `required` list (line 692), (b) the full `lesson_labels` validation block (lines 744–795), (c) `expected_lesson_texts` kwarg (line 662), (d) the `cites_lesson_indices` block, (e) the `analysis` substring rule that bans verbatim non-confirmed lesson_text (~line 832 area), (f) the `_normalize_lesson_text` import at line 337.

---

## Q&A — Decisions Locked (2026-05-12)

### F1 — Do we need a LEARNER step at all?
**Answer:** (a) Keep Learner — same as today; LLM writes reflection after outcome is known.
**MY RECO match:** ✓
**Source:** Round 1

### F2 — Do we need PRIOR REPORTS shown to the predictor?
**Answer:** (a) Keep prior reports — show summaries + links to past learner reports.
**User note:** Scope (ticker / peer / sector inclusion rules) is a separate question in this same questionnaire (P1), not a deferred decision.
**MY RECO match:** ✓
**Source:** Round 1

### F3 — Do we need a MODE flag (historical vs live)?
**Answer:** (a) Two modes, single skill with mode flag.
**MY RECO match:** ✓
**Source:** Round 1

### F4 — Do we need ANY semantic validator beyond JSON shape?
**Answer:** (a) Format + 1 content rule — validator checks shape + ONE anti-lazy rule (exact wording deferred to V1).
**MY RECO match:** ✓
**Source:** Round 2 (re-asked simpler after Round 1 deferral)

### F5 — Structured JSON output, or pure prose?
**Answer:** (a) Structured JSON + auto-rendered .md.
**MY RECO match:** ✓
**Source:** Round 2

### F6 — Do we need a `section_audit.json` step?
**Answer:** (a) Keep section_audit step (two-step pattern).
**MY RECO match:** ✓
**Source:** Round 2

### F7 — Should the architecture allow DATA AGENTS at all?
**Answer:** (a) Support capability, add specific agents later only if a real prediction proves the need.
**MY RECO match:** ✓
**Source:** Round 2

### C1 — Wipe scope (PRECISE via FIX-9, 2026-05-12)
**Answer:** WIDE wipe of generated event artifacts + legacy lesson stores. Top-level tracking + Obsidian linking preserved.

**WIPE (delete contents):**
- All event subdirectories under `earnings-analysis/Companies/*/events/*/`:
  - `context_bundle.json`
  - `context_bundle_rendered.txt`
  - `related_filings/`
  - `prediction/` (and everything in it: result.json, result.md)
  - `learning/` (and everything in it: result.json, result.md)
- Legacy lesson stores: `earnings-analysis/learnings/ticker/*.json` + `earnings-analysis/learnings/global.json` + `earnings-analysis/learnings/global.lock`.

**KEEP (do NOT delete):**
- Top-level tracking files: `earnings-analysis/predictions.csv`, `earnings-analysis/prediction_processed.csv`.
- Obsidian-linking structure: `earnings-analysis/thinking/` and the folder/link skeleton (so links don't break when artifacts are regenerated).
- The `Companies/<TICKER>/events/<QUARTER>/` directory skeleton itself (just empty the contents).

**WHEN:** This wipe happens at cutover/testing time when the new design is ready. NOT now.

**MY RECO match:** ✗ (Round 3 RECO was narrow; user chose wide; FIX-9 made wide-scope precise)
**Source:** Round 3 → FIX-9 precision

### C2 — YAML policy
**Answer:** (a) Keep autogen metadata header on .md (no learner-authored YAML; harmless metadata stays).
**MY RECO match:** ✓
**Source:** Round 3

### C3 — Evidence catalog
**Answer:** (a) Keep strict catalog — every cited fact must resolve to a known ID.
**MY RECO match:** ✓
**Source:** Round 3

### C4 — Modes scope
**Answer:** (a) Build both historical + live modes together as final state.
**MY RECO match:** ✓
**Source:** Round 3

### C5 — Canonical file
**Answer:** (a) JSON canonical, .md auto-rendered from JSON. Code only ever reads JSON.
**MY RECO match:** ✓
**Source:** Round 4

### C6 — Sector/macro agents — build now or later?
**Answer:** Custom — user will build sector/macro fetcher agents SEPARATELY following the `DataSubAgents.md` pattern with PIT-safety. Live mode = IBKR. Historical mode = Polygon (+ maybe Yahoo and other free sources). Capture as a tracked follow-up task; do NOT block restructuring on these.
**MY RECO match:** ≈ (effectively (a) — "not built in restructuring; add later" — with explicit future-task captured)
**Source:** Round 4

### S1 — Prediction JSON shape
**Answer:** (a) STANDARD — drop lesson_labels + cites_lesson_indices; KEEP magnitude_bucket + confidence_bucket; ADD `opened_prior_reports[]` + `pit_mode` (M1 supersedes earlier generic `mode` wording).
**MY RECO match:** ✓
**Source:** Round 4

### S2 — Learner JSON shape (REVISED via FIX-8, 2026-05-12)
**Answer:** Add **2** new fields (not 3): `key_takeaway` (1-sentence summary) + `future_checklist[]` (things to check next time). **TAGS DROPPED.**
**Drop `lesson_audit`** (lessons gone, from Round 4).
**Drop `tags[]`** (no consumer — would be dead weight).

**Original Round 4 answer:** Add all 3 new fields (key_takeaway + future_checklist + tags). FIX-8 dropped tags because nothing else in the locked design reads them.
**MY RECO match:** ≈ (Round 4 RECO included tags; FIX-8 removed them per dead-weight check)
**Source:** Round 4 → FIX-8 revision

### S3 — Schema version names
**Answer:** (a) Fresh start — `prediction_result.v1` (keep) + `learner_result.v1` (rename + reset).
**MY RECO match:** ✓
**Source:** Round 5

### P1 — Prior-report scope
**Answer:** Deferred to Round 6 — user said "own ticker + same-sector" but expressed uncertainty about whether peers are still being calculated. Verified in code: peers ARE calculated by `peer_earnings_snapshot.py` builder. Re-asking with clearer options now that peer status is confirmed.
**Source:** Round 5 deferral

### P2 — Prior-report cap (FINAL via FIX-7, 2026-05-12)
**Answer:** **12 visible reports total**, split as **8 own-ticker + 4 industry-peer**. Each is a SHORT SUMMARY LINE + LINK to the full report — not 12 full reports inline. Reading rules (which get fully opened) live in P8.

**Original Round 5 answer:** 8 total max with no role split. Superseded by FIX-7 which bumped to 12 with explicit role caps to prevent peer crowd-out when own-ticker history is dense.
**MY RECO match:** ≈ (was 8 total cap; bumped to 12 with role split via FIX-7)
**Source:** Round 5 → FIX-7 revision

### P3 — Prior-report ranking (REVISED via FIX-3, 2026-05-12)
**Answer:** Same-ticker first, then INDUSTRY PEERS, recency within each. **No "sector" group in the sort** — P1 excludes sector entirely.

**"Peers" precisely defined:** Neo4j-Industry-matched + market-cap ranked + PIT-safe (as today's `peer_earnings_snapshot.py` already produces). NOT LLM-selected. NOT broadened to sector.

**Empty-peers case:** If Neo4j has no Industry classification or no peers for a ticker, do NOT widen to broad sector. Show no peer reports; rely on own-ticker history only.

**Original Round 5 answer (superseded):** Group + recency with sector as third tier. Sector tier removed because P1 excludes sector.
**MY RECO match:** ✓ (refined)
**Source:** Round 5 → FIX-3 revision

### P1 (RE-ASK) — Prior-report scope
**Answer:** (a) Own ticker + named peers.
**Code-verified clarifications (in response to user's questions):**
- `peer_earnings_snapshot.py:454` confirms peers are ALREADY INDUSTRY-BOUND (not sector-bound). Peers = top-N market-cap tickers within the SAME INDUSTRY as the prediction ticker (e.g., FCX → other Copper industry tickers; not the broader BasicMaterials sector).
- Peers list is NOT LLM-provided. It is derived deterministically from Neo4j entity classification (industry field) + market-cap ranking.
- So "industry if possible" is already what peers IS. No separate industry inclusion needed.
**MY RECO match:** ✓
**Source:** Round 6 (re-asked after Round 5 deferral)

### P4 — Inline summary fields per report
**Answer:** Modified (a) — Date + Ticker + Predicted + Actual + key_takeaway + Link. **TAGS dropped from inline display.**
**User note:** "not sure what role tags play here." Tags would categorize event regime (e.g., "warning-beat", "guidance-raise") for filtering. User decision: not shown inline.
**Implication for S2 (tags[] field):** RESOLVED — FIX-8 dropped `tags[]` from the learner JSON entirely (no consumer = dead weight).
**MY RECO match:** ✗ (RECO included tags; user dropped them from display)
**Source:** Round 6

### P5 — PIT visibility predicate
**Answer:** (a) `learner.pit_cutoff <= predictor.pit_cutoff` — use today's existing PIT logic in code.
**User direction:** "PIT enforcement logic is already correct so use whatever is already in code today."
**MY RECO match:** ✓
**Source:** Round 6

### P6 — Same-quarter self-leak guard
**Answer:** (a) Always exclude — current event never sees its own learner output.
**MY RECO match:** ✓
**Source:** Round 6

### P7 — Path allowlist
**Answer:** (a) Rename `_allowed_learner_paths` → `_allowed_prior_report_paths`; keep prompt-level enforcement.
**MY RECO match:** ✓
**Source:** Round 7

### P8 — Reading discipline
**Answer:** Deferred to Round 8 — user raised a legitimate "forced vs self-select" tradeoff for prediction accuracy. Re-asking with a sharper hybrid option.
**Source:** Round 7 deferral

### P9 — Empty / cold-start case
**Answer:** (a) Fall back to NAMED PEERS only.
**Code-verified clarification (in response to user's question):**
- Peers come from `peer_earnings_snapshot.py:408` — sorted by market cap, top-N within SAME INDUSTRY only. Not LLM-provided.
- We are NOT showing cross-industry reports anywhere in P1's chosen scope (ticker + named peers). All "peer" reports = same-industry top-mkt-cap.
- So P9's cold-start fallback to "named peers" = same-industry only. No widening to cross-industry sector.
**MY RECO match:** ✓
**Source:** Round 7

### P10 — Files linked
**Answer:** (a) Learner reports only — but the inline summary row (P4) always shows `predicted_direction` + `actual_direction` so the "tried vs got" comparison is visible without opening the prediction sidecar.
**MY RECO match:** ✓
**Source:** Round 7

### P8 — Reading discipline (FINAL via FIX-7, 2026-05-12)
**Answer:** Tiered open rule with attention-budget cap.

**Visibility cap (replaces P2):** 12 visible prior reports total, split as:
- max **8 own-ticker** reports
- max **4 industry-peer** reports

**Forced opening:** Predictor MUST fully open the **most-recent 4 own-ticker** reports. These are the highest-signal-by-recency for THIS stock.

**Summary-first (optional open):** Older own-ticker reports (positions 5–8) are summary-first. Predictor opens fully ONLY if the inline summary's takeaway/setup suggests relevance to THIS event.

**Peer reports:** Predictor MAY open up to **3 of the 4 visible peer reports** based on summary relevance. Not forced.

**Recording:** Predictor MUST list which reports were fully opened in the prediction JSON (`opened_prior_reports[]` per S1).

**Rationale (user-stated):** Predictor's job is to price TODAY'S surprise, not absorb full company memory every time. Recent own-ticker = core signal. Older own-ticker = available but stale-risk. Peers can be more relevant DURING the current earnings season.

**Original Round 8 answer (superseded):** Open ALL own-ticker forced + self-select peers. Revised to cap forced opens at recent 4 own-ticker to protect attention budget.
**MY RECO match:** ≈ (FIX-7 added attention-tier refinement; structure preserved)
**Source:** Round 8 → FIX-7 refinement

### P11 — Discovery mechanism
**Answer:** Deferred to Round 9 — user raised a legitimate question comparing filesystem glob vs existing run_ledger. Re-asking with sharper trade-off comparison.
**Source:** Round 8 deferral

### P12 — Learner markdown headings
**Answer:** (a) Today's sections minus lesson sections — Header / Actual Returns / Primary Driver / Contributing Factors / Feedback (Prediction-vs-actual + Why + What worked + What failed) / Key Takeaway / Future Checklist / Evidence Ledger.
**MY RECO match:** ✓
**Source:** Round 8

### V1 — Anti-lazy enforcement layer
**Answer:** (b) Validator HARD-block — rejects the prediction file if a directional call has < 2 grounded source IDs. Bad output never lands on disk.
**MY RECO match:** ✓
**Source:** Round 8

### P11 (RE-ASK) — Discovery mechanism
**Answer:** (a) Filesystem glob — walk `earnings-analysis/Companies/*/events/*/learning/result.json` at bundle-build time. Log + skip on missing/invalid. For every included report, expose the parsed JSON-derived summary fields plus an allowlisted sibling `learning/result.md` path for predictor reading; if the markdown sidecar is missing, regenerate it from JSON rather than parsing markdown as truth.
**MY RECO match:** ✓
**Rationale (locked):** Files on disk = single source of truth; zero state to maintain; no drift risk. run_ledger logs RUNS not OUTPUTS (failed runs have ledger entries but no result.json), needs filtering, and wasn't designed for this query pattern.
**Source:** Round 9 (re-asked after Round 8 deferral)

### V2 — Grounded source definition
**Answer:** (a) Mixed — ≥1 of the 2 grounded source IDs MUST be from THIS bundle (current event evidence); the other(s) can be this-bundle or prior-report.
**MY RECO match:** ✓
**Source:** Round 9

### V3 — Live tool evidence IDs
**Answer:** (a) Runtime IDs like `SRC:LIVE:WEB:001`, `SRC:LIVE:IBKR:001`. Validator accepts the `SRC:LIVE:*` prefix.
**MY RECO match:** ✓
**Source:** Round 9

### V4 — Validation strictness
**Answer:** (a) Mode-split — historical strict (catalog grounding); live strict but accepts SRC:LIVE:* runtime IDs (per V3).
**MY RECO match:** ✓
**Source:** Round 9

### V5 — no_call requirements (REFINED via FIX-6, 2026-05-12)
**Answer:** Two valid no_call paths; predictor MUST pick one explicitly. Validator accepts either.

**Path 1 — BALANCED:** Predictor sees roughly equal evidence on both sides.
- MUST list ≥1 long driver AND ≥1 short driver in `key_drivers`.
- Each driver must have non-empty `evidence`.
- Shows the balance/conflict explicitly.

**Path 2 — MISSING DATA:** Predictor lacks evidence to call either side.
- MUST list specific missing items in `data_gaps[]` (e.g., "consensus unavailable", "guidance not provided", "no peer reactions in bundle").
- `key_drivers` may be empty.
- Must NOT fake opposing drivers.
- Forces honest "I don't have enough" rather than invented drivers.

**Validator rule:** `direction == "no_call"` REQUIRES either (Path 1: `len(key_drivers) >= 2` with both directions present) OR (Path 2: `len(data_gaps) >= 1` AND analysis text explains the missing-data reason).

**Original Round 10 answer (superseded):** Single-path "≥1 driver each side" (which would have forced fake drivers when data is missing). Refined here to prevent fabrication.
**MY RECO match:** ✗ → ≈ (RECO was option (a) "analysis text"; user picked stricter; FIX-6 added missing-data exception)
**Source:** Round 10 → FIX-6 refinement

### M1 — Mode flag location
**Answer:** (a) Reuse `pit_mode` field name — orchestrator stamps it into the predictor bundle at build time. Same field used by both predictor bundle + learner output.
**MY RECO match:** ✓
**Source:** Round 10

### M2 — Tool gating mechanism (CLARIFIED via FIX-5, 2026-05-12)
**Answer:** (a) ONE skill, orchestrator passes mode-specific `allowed_tools=[...]` at each SDK invocation.

**Clarification (per FIX-5):** The K8s earnings-worker (per E1/FIX-4) spawns `earnings_orchestrator.py` as a subprocess. The ORCHESTRATOR is what actually invokes the SDK call with mode-specific `allowed_tools` — the worker is upstream plumbing that delivers the job to the orchestrator. So "orchestrator passes allowed_tools" is correct even though the K8s worker is the outer container.

**MY RECO match:** ✓
**Source:** Round 10 → FIX-5 clarification

### M3 — Historical tool allowlist
**Answer:** (a) Read + Bash + DataSubAgents Task.
**User note:** Some individual DataSubAgents may not be 100% PIT-compliant; need a per-agent audit before flipping the switch.
**MY RECO match:** ✓
**Source:** Round 10

### M4 — Live mode profile (BALANCED+, SLA-clarified via FIX-10, 2026-05-12)
**Answer:** BALANCED profile. **SLA applies to LIVE prediction only.** Historical mode uses looser timing.

**Tools:** DataSubAgents + WebFetch + Neo4j read + IBKR.

**Live SLA (tiered):**
- **90s — soft warning injected.** Predictor sees "approaching target."
- **120s — operating target.** Predictor MUST ship best-available call AT this mark, UNLESS it is actively resolving a SPECIFIC material uncertainty that could change the direction (e.g., a tool call is in-flight that will fetch a decisive fact). Mere "I want more time to think" does not qualify.
- **300s — hard kill.** Safety net, not the normal runtime. Orchestrator force-terminates the predictor SDK then executes this fallback flow (per CLEANUP-7):
  1. If `prediction/result.json` EXISTS and passes the v1 validator → keep it; stamp `timeout_after_valid_write=true` in run-ledger metadata.
  2. If `prediction/result.json` is missing or invalid → orchestrator writes a VALID live no_call fallback: `{direction: "no_call", confidence_score: 0, expected_move_range_pct: [0, 0], pit_mode: "live", data_gaps: ["live_timeout"], opened_prior_reports: [<whatever was logged before kill>], analysis: "Hard timeout at 300s — no valid prediction written before kill."}` plus `timeout=true` metadata.
  3. Close the run as `completed-timeout` (NOT ordinary success). Learner pipeline still fires per normal next-event trigger.

**Tool calls:** 15 default; allow up to 20 within the 300s hard cap if needed.

**Report opens:** Per P8 (FIX-7 revised) — up to 4 forced own-ticker + up to 3 peers = up to 7 full opens.

**time_since_release:** Visible throughout if easy to wire; otherwise inject ONCE at kickoff + enforce hard timeout at 300s.

**Operating expectation:** Median live runtime should be ~90-120s. >120s only when material uncertainty is actively resolving. 300s is exceptional.

**MY RECO match:** ≈ (RECO was 90s/15 calls; user extended to 300s/120s/90s tiered SLA with material-uncertainty escape; FIX-10 clarified the operating expectation)
**Source:** Round 11 → FIX-10 SLA clarification

### M5 — Learner timing in live mode (just-in-time, not scheduled)
**Answer:** Learner runs BEFORE the next prediction for that ticker/event sequence — not necessarily exactly 3 months later. Just-in-time: if a new prediction is about to start for the same ticker AND no learner has run since the previous prediction's outcome was knowable, fire the learner first.
**MY RECO match:** ✗ (RECO was "next morning after daily-stock ingest"; user simpler approach: trigger learner just-in-time before next prediction, no scheduled cron needed)
**Rationale (user's):** Avoids live-mode learner scheduling complexity. Learner report is only needed before the next prediction, so generate it on-demand at that moment.
**Source:** Round 11

### E1 — Predictor execution architecture (LOCKED via FIX-4, 2026-05-12)
**Answer:** Build per `.claude/plans/EarningsTrigger.md` design. K8s pipeline is the FINAL STATE — confirmed after explicit scope-risk re-ask.

**Exact architecture (locked):**
- **Separate** `earnings-trigger` daemon (NOT shared with `extract:pipeline`).
- **Warm-start-aware daemon/walker.** Historical backfill starts at the warm-start anchor from EarningsTrigger.md: the earliest earnings 8-K with a usable PIT-visible prior 10-Q/10-K. Pre-anchor quarters do not block prior-chain gates; if no anchor exists, log/skip `SKIP no_warm_start_anchor` rather than failing.
- **Separate** `earnings-worker` (NOT shared with extraction-worker).
- **Dedicated Redis queue:** `earnings:pipeline`.
- **Redis leases** on each job for retry safety.
- **Explicit `complete.json` sentinels** for both prediction + learner (per EarningsTrigger.md §1 — `result.json` alone is NOT safe completion truth under retries/re-entry).
- **Worker invokes `earnings_orchestrator.py` as a subprocess.** The worker is a thin shell; the orchestrator owns all the difficult semantics.

**What the worker does NOT own:**
- PIT logic
- Quarter identity validation
- Bundle assembly
- Learner recovery
- Lesson library writes
- (Anything in `earnings_orchestrator.py` today — preserved.)

**User rationale (verbatim):** "I understand it is not the fewest lines of code, but it matches the existing guidance extraction operating model I already use: always-on trigger daemon → Redis queue → KEDA worker → Claude/SDK execution → durable status/retry. For me, 'simplest' means one familiar production pattern, not a second special-case in-process runner."

**MY RECO match:** ≈ (RECO was "in-process SDK simpler"; user picked K8s pipeline based on operational-consistency reasoning. Valid trade-off.)
**Source:** Round 11 → FIX-4 reconfirmation
**Reference doc:** `.claude/plans/EarningsTrigger.md` (already exists, 68KB, design-locked since 2026-04-19).

### O1 — Drop disposition
**Answer:** (a) Delete `predictor_lessons` + `global_observations` + `data_lessons`; KEEP `section_audit.json` (per F6).
**Note:** `future_checklist` is a brand-new field, not a rename of `data_lessons`.
**MY RECO match:** ✓
**Source:** Round 11

### O2 — Prior Report Links section render format
**Answer:** (b) Bulleted list per report — multi-line bullet showing Ticker + Quarter + Date, predicted/actual on the next line, key_takeaway in quotes, and a Link line.
**MY RECO match:** ✗ (RECO was compact table; user picked bulleted list for readability)
**Source:** Round 12

### EV1 — Evaluation metrics
**Answer:** (a) STANDARD — direction accuracy + signed-midpoint MSE + Brier score (confidence calibration).
**Implementation note (2026-05-15):** EV1 is a deterministic scorer over each finished `prediction/result.json` + actual post-earnings return, comparing `direction`, `confidence`, and `expected_move_range_pct` against reality, then aggregating by ticker/quarter/replay suite for accuracy, calibration, signed error/MSE, and realized directional edge.
**MY RECO match:** ✓
**Source:** Round 12

---

## Q&A Completion Summary (2026-05-12)

All **42** questions answered across **12 rounds**.

**Breakdown of recommendation alignment (POST-FIX, 2026-05-12):**
- **✓ Clean RECO match: 31 of 42 (~74%)**
- **≈ Modified RECO (kept the spirit with FIX-* tweaks): 7 of 42 (~17%)**
  - C6 sector/macro agents — user will build separately per DataSubAgents pattern (TASK-1)
  - S2 learner schema — added 2 of 3 proposed new fields; tags dropped via FIX-8
  - P2 cap — was 8 total; bumped to 12 (8 own + 4 peer) via FIX-7
  - P8 reading discipline — added attention-tier refinement via FIX-7
  - M4 live profile — BALANCED+ with extended timing (300s hard / 120s target / 90s soft) per FIX-10
  - E1 execution architecture — both predictor + learner via the K8s pipeline pattern (per EarningsTrigger.md, confirmed via FIX-4)
  - V5 no_call — user picked stricter "≥1 driver each side"; FIX-6 added missing-data exception path
- **✗ True divergence from RECO: 4 of 42 (~9%)**
  - C1 wipe scope — user picked WIDE (with Obsidian linking preservation); FIX-9 made scope precise
  - P4 inline summary — drop `tags` column from display (consistent with FIX-8 tag removal)
  - M5 learner timing in live — just-in-time before next prediction (no scheduled cron)
  - O2 render format — bulleted list per report (not compact table)

**Open follow-ups / implementation flags:**
1. TASK-1 — Build sector + macro DataSubAgents (PIT-aware; live=IBKR, historical=Polygon+Yahoo).
2. TASK-2 — Per-DataSubAgent PIT-compliance audit before historical-mode flip.
3. **E1 scope expansion noted** — moving BOTH predictor + learner to K8s-worker SDK pattern (`extraction-pipeline-reference.md`) is bigger than original "move predictor to SDK-embed" — confirm full scope before implementation begins.
4. ~~P4 vs S2 tag question~~ — **RESOLVED via FIX-8:** `tags[]` dropped entirely from S2 (no consumer).

The decision questionnaire phase is **complete**. Next phase: implementation plan that respects these 42 locked decisions.

---

## Code Verification Pass (2026-05-15)

Purpose: compare this target architecture against the actual repository state before using this document as implementation truth. This pass changed **documentation only**; it did not implement the rewrite.

### Important Corrections From Code Audit

1. **Anti-lazy enforcement is NOT current code.** Current predictor prompt has evidence-ledger source-ID grounding and a non-lesson key-driver grounding rule, but no ≥2 directional source-ID rule; current `validate_prediction_result` also does not hard-block directional calls with fewer than 2 grounded source IDs. V1/V2 below are target work: predictor prompt + validator hard-block, with ≥1 source ID from the current bundle.
2. **MSE/Brier are NOT current code.** Current code emits `expected_move_range_pct` and derives `magnitude_bucket` from the range midpoint, but no backtest MSE or Brier implementation was found in `scripts/`. EV1 is target work.
3. **The canonical mode field is `pit_mode`, not `mode`.** `_resolve_pit_mode` already returns `historical`/`live`, and M1 locks the shared field name as `pit_mode`. Any older `mode` wording in this plan is superseded.
4. **Report-opening is forced for the most-recent 4 own-ticker reports.** The predictor only selects optional older own-ticker and peer reports after those forced opens. P8/FIX-7 is the controlling rule.
5. **`EarningsTrigger.md` is useful for K8s worker boundaries but still contains old lesson-loop language.** Use it for `complete.json`, Redis queue, trigger/worker split, and subprocess boundary; do not inherit its old lesson persistence semantics.
6. **Current learner schema strings are split/stale, but the target remains `learner_result.v1`.** `validate_learning.py` + learner skill currently enforce `attribution_result.v3`; `result_md_renderer.py` docstrings still say `attribution_result.v2`. Since lesson semantics are being removed, do not preserve either attribution schema name — reconcile all of them into the locked `learner_result.v1` target.

### Actual Production State Today

| Surface | Actual Code State | Target Delta |
|---|---|---|
| Bundle memory | `build_prediction_bundle` still builds `learning_context` (`scripts/earnings/earnings_orchestrator.py:196`, `252-275`). | Replace with `prior_reports_context`. |
| Bundle renderer | `renderer/bundle.py` imports and renders `_render_learning_context`; `renderer/lessons.py` renders `## Prior Lessons (from learner)` plus `## Lessons To Label`. | Delete lesson renderer, add prior-report renderer. |
| Evidence catalog | `build_evidence_source_catalog` maps `learning_context` to `S10.lessons` and emits `#S10.lesson.L<n>` anchors. | Replace with `#S10.report.R<n>` and live/agent anchors. |
| Prediction validator | `validate_prediction_result` requires `lesson_labels`, validates lesson text/counts, validates `cites_lesson_indices`, and enforces U67 evidence grounding. | Keep schema/range/evidence grounding; remove lesson rules; add anti-lazy/no_call rules. |
| Prediction result writer | `finalize_prediction_result` writes `schema_version="prediction_result.v1"` and derives magnitude/confidence buckets. It does not stamp `pit_mode` or `opened_prior_reports`. | Add target fields while keeping `prediction_result.v1` per S3 unless a later approved design explicitly reopens the schema name. |
| Predictor prompt builder | `_build_predictor_prompt` has no direct lesson logic; it passes bundle/render/audit/result paths. | Upstream rendered bundle + skill rewrite are the meaningful changes. |
| Predictor SDK call | `_run_predictor_via_sdk` uses Claude SDK with `permission_mode="bypassPermissions"` and no mode-specific `allowed_tools`, SLA, or timeout fallback. | Add mode-aware tool gating and live SLA. |
| Learner skill/validator | `.claude/skills/earnings-learner/SKILL.md` and `validate_learning.py` are still `attribution_result.v3` and lesson-audit/global-observation heavy. | Rewrite to `learner_result.v1` causal report. |
| Learner output rendering | `result_md_renderer.py` renders predictor/data lessons, global observations, and lesson audit-era fields. Docstrings still reference `attribution_result.v2` in places. | Render primary driver, contributing factors, feedback, key takeaway, future checklist, evidence ledger. |
| Learner persistence | `run_learner_for_quarter` still calls lesson append/recovery/audit aggregation paths. | Existing valid `learning/result.json` is recovered; no derived lesson writes. |
| Hooks | `.claude/hooks/validate_learning_output.py` correctly matches `/learning/result.json`, but its comment/schema naming is stale. | Keep wrapper; point to new learner validator/schema. |
| Builders | All 8 builder files under `scripts/earnings/builders/` are lesson-clean. Peer earnings already uses same-industry peers ranked by market cap. | Keep. |
| Non-lesson renderers | Renderer files other than `bundle.py`, `lessons.py`, and `__init__.py` are lesson-clean. | Keep. |
| `run_ledger.py` | Lesson-clean. | Keep. |
| `_atomic_write_json` | Shared utility used outside lessons. | Keep. |

### Current Lesson-Bound Orchestrator Surfaces

Delete or rewrite these only as part of the actual implementation pass:

- Remove lesson store/audit functions: `_stamp_ticker_lesson_row`, `append_ticker_lesson`, `append_global_lessons`, `_assert_learner_paths_invariant` (replace smaller prior-report invariant), `DuplicateLessonIdError`, `_routing_key_from_source`, `compute_lesson_id`, `_content_matches`, `assert_no_id_collision`, `compute_status`, `_passes_audit_pit`, `_apply_render_view`, `_stamp_quarter_row_skeleton`, `_upsert_audit_in_history`, `_apply_audit_ticker`, `_apply_audit_global`, `_apply_audit_and_append_global_atomic`, `_append_lesson_row_to_ticker_quarter`, `_register_replacement`, `aggregate_lesson_audits`, `_validate_audit_against_prediction`.
- Rewrite `build_learning_context` → `build_prior_reports_context`.
- Rewrite `_decorate_with_learner_paths` to preserve PIT self-guard + allowlist assembly while attaching prior-report summaries/links instead of lesson entries.
- Remove `_text_utils.py` only after dropping all orchestrator references to `_normalize_lesson_text` and `iter_labeled_lessons`.

### Test and Golden Inventory From Grep

Lesson-touching Python/helper files found by `rg` on 2026-05-15: **29** files.

1. `scripts/earnings/test_finalize_session_id_preservation.py`
2. `scripts/earnings/test_render_learning_context.py`
3. `scripts/earnings/test_build_learning_context_paths.py`
4. `scripts/earnings/tests/_degraded_fixtures.py`
5. `scripts/earnings/test_migrate_unified_layout.py`
6. `scripts/earnings/tests/_capture_golden.py`
7. `scripts/earnings/test_result_md_renderer.py`
8. `scripts/earnings/test_loop_round_trip_smoke.py`
9. `scripts/earnings/test_lesson_status_transitions.py`
10. `scripts/earnings/test_evidence_refs_resolve.py`
11. `scripts/earnings/test_audit_history_pit_filter.py`
12. `scripts/earnings/test_lesson_id_stability.py`
13. `scripts/earnings/test_renderer_imports.py`
14. `scripts/earnings/test_pit_self_leak_guard.py`
15. `scripts/earnings/test_aggregator_recovery_path.py`
16. `scripts/earnings/test_renderer_helpers.py`
17. `scripts/earnings/test_learning_context.py`
18. `scripts/earnings/test_validate_learning_v3.py`
19. `scripts/earnings/test_validate_prediction_u67.py`
20. `scripts/earnings/test_aggregate_lesson_audits.py`
21. `scripts/earnings/test_validate_learning_totality.py`
22. `scripts/earnings/test_learner_paths_cross_surface.py`
23. `scripts/earnings/test_iter_labeled_lessons_v2.py`
24. `scripts/earnings/test_validate_prediction_result.py`
25. `scripts/earnings/test_renderer_golden_sections.py`
26. `scripts/earnings/test_orchestrator_cross_file_validation.py`
27. `scripts/earnings/test_thinking_harvester.py`
28. `scripts/earnings/test_section_audit_feature.py`
29. `scripts/earnings/test_render_lessons_v2.py`

Lesson-touching fixture/golden files found by content `rg` on 2026-05-15: **29** files.

1. `scripts/earnings/tests/fixtures/golden_bundles/AVGO_Q3_FY2023.json`
2. `scripts/earnings/tests/fixtures/golden_bundles/AVGO_Q4_FY2023.json`
3. `scripts/earnings/tests/fixtures/golden_bundles/CHRW_Q4_FY2025.json`
4. `scripts/earnings/tests/fixtures/golden_bundles/CXM_Q4_FY2026.json`
5. `scripts/earnings/tests/fixtures/golden_renders/degraded/all_builder_errors.txt`
6. `scripts/earnings/tests/fixtures/golden_renders/degraded/all_no_data.txt`
7. `scripts/earnings/tests/fixtures/golden_renders/degraded/empty_quarter_label.txt`
8. `scripts/earnings/tests/fixtures/golden_renders/degraded/guidance_all_units.txt`
9. `scripts/earnings/tests/fixtures/golden_renders/degraded/guidance_qual_only.txt`
10. `scripts/earnings/tests/fixtures/golden_renders/degraded/huge_and_tiny.txt`
11. `scripts/earnings/tests/fixtures/golden_renders/degraded/iq_no_events.txt`
12. `scripts/earnings/tests/fixtures/golden_renders/degraded/iq_pipe_in_title.txt`
13. `scripts/earnings/tests/fixtures/golden_renders/degraded/no_current_quarter.txt`
14. `scripts/earnings/tests/fixtures/golden_renders/degraded/no_ex991.txt`
15. `scripts/earnings/tests/fixtures/golden_renders/degraded/no_lessons.txt`
16. `scripts/earnings/tests/fixtures/golden_renders/degraded/non_finite_numbers.txt`
17. `scripts/earnings/tests/fixtures/golden_renders/degraded/unicode_in_text.txt`
18. `scripts/earnings/tests/fixtures/golden_renders/full/AVGO_Q3_FY2023.txt`
19. `scripts/earnings/tests/fixtures/golden_renders/full/AVGO_Q4_FY2023.txt`
20. `scripts/earnings/tests/fixtures/golden_renders/full/CHRW_Q4_FY2025.txt`
21. `scripts/earnings/tests/fixtures/golden_renders/full/CXM_Q4_FY2026.txt`
22. `scripts/earnings/tests/fixtures/golden_renders/full/NFLX_Q3_FY2025.txt`
23. `scripts/earnings/tests/fixtures/golden_renders/sections/lessons/AVGO_Q3_FY2023.txt`
24. `scripts/earnings/tests/fixtures/golden_renders/sections/lessons/AVGO_Q4_FY2023.txt`
25. `scripts/earnings/tests/fixtures/golden_renders/sections/lessons/CHRW_Q4_FY2025.txt`
26. `scripts/earnings/tests/fixtures/golden_renders/sections/lessons/CXM_Q4_FY2026.txt`
27. `scripts/earnings/tests/fixtures/guidance_session.jsonl`
28. `scripts/earnings/tests/fixtures/learner_session.jsonl`
29. `scripts/earnings/tests/fixtures/predictor_session/subagents/agent-a9f59960218dbbe88.jsonl`

Direct lesson-render golden paths by directory/name: **9** files — the 8 files under `scripts/earnings/tests/fixtures/golden_renders/sections/lessons/` (4 `.txt` + 4 `.json`) plus `scripts/earnings/tests/fixtures/golden_renders/degraded/no_lessons.txt`. The content-grep inventory above is broader because full/degraded renders, bundle fixtures, and JSONL fixtures also contain lesson-era strings.

### External Plan Cross-Checks

- `.claude/plans/DataSubAgents.md` remains the right PIT-safe subagent contract source. PredictorLearnerFinal intentionally defers sector/macro subagent construction and requires a per-agent PIT audit before historical live-up.
- `.claude/plans/LearnerLoopPlans/LearnerLoopPlan_LessonIntelligence_Minimal.md` is a lesson-lifecycle design and does not apply wholesale. The useful borrowed pieces are already represented here as bundle-primary anchoring, anti-lazy grounding, EV metrics, and no_call handling.
- `.claude/plans/EarningsTrigger.md` confirms the `complete.json` sentinel, Redis `earnings:pipeline`, `earnings-trigger` / `earnings-worker`, and worker-invokes-orchestrator boundary. It still needs vocabulary cleanup if copied into the final blueprint.
  - **When copying EarningsTrigger.md into the blueprint, scrub its old lesson vocabulary but keep the warm-start mechanism verbatim.** EarningsTrigger.md predates the lesson removal and still contains lesson-loop persistence wording (lesson stores, audits, lesson-chain language) — that wording must be rewritten to the `prior_reports_context` / `learner_result.v1` target surface. However, the **warm-start anchor** (EarningsTrigger.md §"Warm-start anchor (locked requirement)") is a daemon/walker quarter-chain scheduling rule, **not** lesson logic: for a ticker it is the earliest 8-K whose `filed_8k` has at least one usable prior periodic filing; quarters before it are pre-history (skip, do not treat as missing chain work; `SKIP no_warm_start_anchor` when none exists). It is lesson-independent, still required for clean scheduling, and backed at runtime by the orchestrator's `resolve_quarter_info()` FAIL_CLOSED guard (which the target state keeps unchanged per P5). Copy the warm-start anchor + its prior-chain sentinel checks **exactly as written** — only the artifact the chain points at changes (now `learning/complete.json` for the `learner_result.v1` causal report instead of lesson outputs). Do not simplify, re-derive, or merge it during the vocabulary scrub.

---

## Tracked Follow-Up Tasks (continued)

### TASK-2 — Per-DataSubAgent PIT-compliance audit (from M3, 2026-05-12)
**What:** Audit each DataSubAgent in `.claude/agents/*.md` against the PIT contract in `.claude/plans/DataSubAgents.md`. Flag any agent that is NOT 100% PIT-compliant for historical-mode use.
**Why:** M3 allows DataSubAgents in historical mode by default, but a non-PIT-compliant agent would silently leak future data. Need explicit per-agent classification.
**Deliverable:** A table or check list noting each agent's PIT status (compliant / partial / non-compliant) so historical-mode tool gating can blocklist non-compliant agents.
**Status:** Captured. Not part of the restructuring scope but must be done before historical-mode goes live.

---

## Tracked Follow-Up Tasks (do AFTER restructuring; do not block it)

### TASK-1 — Build sector + macro data sub-agents (from C6, 2026-05-12)
**What:** Build dedicated sector + macro fetcher sub-agents following the `.claude/plans/DataSubAgents.md` pattern.
**Requirements:**
- PIT-safety (`--pit` flag, retry on contamination).
- Mode-aware data sources:
  - **Live mode:** IBKR (already subscribed; covers stocks + sector ETFs + indices).
  - **Historical mode:** Polygon (PIT-snapshot), possibly Yahoo and other free resources.
- Same JSON envelope contract as existing DataSubAgents.
- Triggered on-demand by predictor (live) or learner (any mode) when sector/macro context is needed beyond the bundle's macro_snapshot.
**Status:** Captured here so it's not lost. Not part of the predictor/learner restructuring scope.

---

## Next Step — Implementation Blueprint Pass (no code yet)

**Decided 2026-05-12 after independent Claude + ChatGPT review.**

### Why this step (not more design questions, not coding yet)

The design is locked. The 42 decisions + 10 FIX-* + 7 CLEANUP-* entries above cover every architectural choice. More design questions would create churn without adding clarity.

But handing this doc directly to a coding bot is risky. The current code has many lesson-related tendrils. The failure mode now is not wrong philosophy; it is **missed callsites, schema drift, broken tests, or half-removed lesson logic.**

**The bridge between locked decisions and clean code is one rigorous implementation blueprint.**

### The next-step instruction (verbatim — to be sent to a fresh Claude session)

> Now do an implementation blueprint pass, not coding.
>
> Read `PredictorLearnerFinal.md` and the current codebase. Produce a **file-by-file implementation contract** for the final simplified predictor/learner architecture.
>
> For each file/function/test, classify as **KEEP / DELETE / REWRITE / ADD**, with the exact reason and target behavior.
>
> Include exact:
> - `prediction_result.v1` and `learner_result.v1` JSON schemas (field-by-field with types + required/optional).
> - `prior_reports_context` shape on the bundle.
> - Validator rules (anti-lazy `≥2 grounded source IDs` + `no_call` two-path contract).
> - Live timeout fallback behavior (90s soft / 120s ship / 300s hard-kill flow per M4 + CLEANUP-7).
> - K8s worker / orchestrator boundary per EarningsTrigger.md (separate `earnings-trigger`, `earnings-worker`, `earnings:pipeline` queue; worker invokes `earnings_orchestrator.py` as subprocess; PIT/quarter logic stays in orchestrator).
> - Test + golden updates (per-file delete/rewrite/keep list across the 29 lesson-touching Python/helper files, 29 content-grep lesson-touching fixture/golden files, and the 9 direct lesson-render golden paths).
>
> End with:
> 1. **Remaining ambiguities**, if any.
> 2. **Safest implementation order** (stage-by-stage, with validation gate between stages).
> 3. **Acceptance tests** proving the rewrite is complete.
> 4. **Grep checks** proving lesson machinery is gone.
>
> Do not write code yet.

### Deliverable structure (what the blueprint should contain)

| Section | Purpose |
|---|---|
| **Schemas (exact)** | `prediction_result.v1` + `learner_result.v1` + `prior_reports_context` — field-by-field with types, required/optional, examples |
| **SKILL.md drafts (full text)** | Complete rewritten text for `earnings-prediction/SKILL.md` and `earnings-learner/SKILL.md` |
| **Validator code spec** | Rule-by-rule logic for the rewritten validator (anti-lazy, no_call two-path, evidence catalog grounding, live runtime IDs) |
| **Orchestrator surgery** | Function-by-function table: delete / rewrite / keep; with line refs to current `earnings_orchestrator.py` |
| **Renderer rewrite** | New Section 10 "Prior Reports" bulleted layout (per O2) + how `prior_reports_context` flows through |
| **K8s pipeline (YAMLs)** | `earnings-trigger` + `earnings-worker` manifests + Redis `earnings:pipeline` queue + KEDA scaler |
| **Discovery code** | Filesystem glob + error paths + `complete.json` sentinel contract |
| **Tests** | Per-file table across the 29 lesson-touching Python/helper files: delete / rewrite (with new behavior) / keep |
| **Goldens** | Per-file table across the 29 content-grep lesson-touching fixture/golden files plus the 9 direct lesson-render golden paths: regenerate (when) / keep |
| **Wipe + Obsidian preservation** | Exact `rm` + `mkdir` commands; what's wiped, what's preserved, when this runs |
| **E2E smoke** | Concrete validation: replay FCX Q1 2026 through the new pipeline + verify all gates pass |

### Each stage in the blueprint has

- **INPUTS** — current files affected
- **OUTPUTS** — new/changed files
- **VALIDATION GATE** — the test or grep that proves the stage is done
- **ROLLBACK** — what to revert if the gate fails

### Iteration pattern

1. I (or a fresh Claude session) draft the blueprint as `ImplementationPlan.md`.
2. You + ChatGPT review the BLUEPRINT (not more Q&A).
3. Iterate on the blueprint until both reviewers accept.
4. Coding bot then executes the blueprint stage-by-stage (each stage = one PR).

### Explicit non-goals for this step

- ❌ More design questions (decisions are locked).
- ❌ Coding (premature without the blueprint).
- ❌ Re-evaluating any of the 42 + FIX + CLEANUP decisions (unless the blueprint pass surfaces a genuine implementation impossibility).

### Acceptance criteria for the blueprint itself

A senior engineer reading the blueprint cold should be able to:
1. Open any file mentioned and know exactly what to delete / rewrite / keep.
2. Find the exact target JSON schema for every artifact.
3. See the stage order + validation gates so they can stop at any gate if something breaks.
4. Run the grep checks at the end to prove no lesson code survived.

Without all four, the blueprint is not done.

---

## Bot-Safe Transition Protocol (2026-05-15)

> Converged Claude + ChatGPT execution discipline. The blueprint above says *what* to build; this says *how to roll it out* so a bot cannot cause silent regression. Hand bots **one stage at a time**. A stage is done only when its scripted gate exits 0.

### Cross-cutting rules (apply to EVERY stage)

- **Writer bot ≠ reviewer bot.** Writer implements; a fresh reviewer bot checks blueprint-conformance and runs the gate. No bot certifies its own work.
- **Anchors, not line numbers.** Plan/blueprint line numbers are known stale (~2766 off on prompt builders). Bots must re-locate every edit by function name / grep pattern at edit time.
- **No assertion weakening.** A bot may not delete or loosen a test assertion to go green. Test changes must be pre-listed in the blueprint test plan; unlisted changes = auto-reject.
- **Stop-on-red.** Any gate failure → revert that PR, do not proceed. No partial merges.
- **Fail closed.** Invalid prior-report JSON → log+skip. Invalid prediction/learner JSON → reject (retry where applicable). Live timeout with no valid output → write valid timeout `no_call`. Forbidden token present → gate fails.
- **One stage = one PR = one revert unit** (except WIPE — Stage 6, irreversible).
- **SDK-invocation hardening.** The orchestrator's `_run_predictor_via_sdk` /
  `_run_learner_via_sdk` must set an adequate `max_buffer_size` on
  `ClaudeAgentOptions` (large rendered bundles / 8-K packets / learner evidence can
  exceed SDK defaults → silent truncation = corrupted artifact). Verify-not-assume:
  confirm it's set (≥10 MB) before Stage 5 E2E. (Confirmed canonical pattern from
  Anthropic's `claude_agent_sdk/research_agent`.)

### Split baseline oracle (built in Stage 0; used by every gate)

- **Deterministic tier** — 7 builder outputs, bundle JSON, renderer output (rendered from FROZEN input JSON). Gate = **byte-identical** before vs after (modulo the intentionally removed field).
- **LLM tier** — predictor/learner outputs. **Never byte-compared.** Gate = schema-valid + structural invariants + EV metrics on a held replay set. Lesson-era accuracy parity is **out of scope by design**; EV metrics set a NEW post-cutover baseline.

### Stages (hand to bots one by one)

**Stage 0 — LOCK + BASELINE (no code).** Produce locked `ImplementationPlan.md`: exact schemas, file actions, anchors/patterns, and the attribution-result schema reconciliation already locked by S3 (`prediction_result.v1` stays; all attribution-result strings become `learner_result.v1`). Seal the split oracle (deterministic artifacts + git SHA + model/prompt versions, read-only). *Gate:* reviewer bot confirms zero open ambiguities, schemas complete, no trusted stale line numbers.

**Stage 1 — ADD side-by-side.** Add new schema validators, `prior_reports_context` discovery, renderer Section 10, new validator rules — ALONGSIDE lesson code (lessons still present & dormant). *Gate:* new unit tests pass; full old suite still 100% green; deterministic oracle byte-identical.

**Stage 2 — SWITCH.** Repoint orchestrator/skills to the new surface; gate tools by `pit_mode`. Old lesson code present but unreferenced. Migrate shared-surface tests **in this PR** (they break here, not at delete). *Gate:* E2E replay emits valid new-schema prediction+learner across the replay matrix; deterministic oracle byte-identical; grep proves old lesson code has zero live callers.

**Stage 3 — DELETE dead lesson code.** Remove lesson functions/files/stores/audits (now provably unreferenced). *Gate:* import graph intact; pyflakes clean; full pytest green; scoped forbidden-token gate == 0.

**Stage 4 — MIGRATE tests/goldens.** Delete lesson-only tests; rewrite shared; regenerate ONLY pre-authorized goldens (renderer goldens from frozen input JSON). *Gate:* golden diff scope == authorized set; reviewer bot confirms each new golden encodes TARGET behavior, not emitted output; deterministic oracle still byte-identical.

**Stage 5 — FRESH E2E (before wipe).** Full replay matrix end-to-end through trigger→Redis→worker→orchestrator. *Gate:* all schema + structural + fail-closed gates pass on every matrix case.

**Stage 6 — WIPE (irreversible — last).** Quiesce the live pipeline. `tar` the corpus as zero-cost insurance. Then `rm` per FIX-9 scope; assert Obsidian/CSV preservation. *Gate:* preservation assertions pass; fresh corpus regenerates cleanly from the new architecture.

### Scoped forbidden-token gate (Stage 3+ release gate)

Fails on any occurrence in production/test surfaces (archived docs explicitly allowlisted):
`lesson_labels`, `cites_lesson_indices`, `lesson_audit`, `predictor_lessons`, `data_lessons`, `global_observations`, `ticker_lessons`, `global_lessons`, `learning_context` — and `attribution_result` **only after** the Stage-0 v2/v3 decision is locked.

### Replay matrix (Stage 2 & 5 E2E)

FCX Q1/Q3 path · a ticker with no own history · a ticker with peers · a no-peer case · a `no_call` missing-data fixture · a live-timeout fallback simulation.

---

## Standing Checklist — Learner⇄Predictor Feedback Loop (2026-05-15)

> Status: converged 2026-05-15. AUGMENTS the locked target state — modifies none of the
> 42 decisions / FIX / CLEANUP. One sub-decision PARKED (see below). Single target state,
> no v0/v1 staging. Never call this a "lesson" — the word drags lifecycle gravity back.

### Why it exists
Managed lessons were rejected as unwieldy. The free-form prior-reports design has one
gap: sharp, hard-won checks age out of the recency window. This closes it with near-zero
machinery by reusing an artifact that already exists: `learner_result.v1.future_checklist`.
It is NOT an alpha source. Honest framing: a low-cost, asymmetric, compounding
error-suppressor — modest on average, high-value on repeated idiosyncratic mistakes for
repeatedly-predicted tickers, ~zero early. Kept on payoff shape, not average effect.

### The loop (one artifact; no state beyond it)
    LEARNER (post-outcome) — reviews recent PIT-visible own-ticker FULL reports
      (already surfaced by the prior-report plumbing; window N parked) + this
      prediction + actual outcome → CONSOLIDATES one new future_checklist
        → ORCHESTRATOR pipes the latest allowed own-ticker list into the next bundle
          → PREDICTOR engages relevant items in its analysis prose
            → outcome known → next LEARNER rewrites it → loop
The correction lives in the learner's reasoning each cycle. Nothing new is stored.

### Rules (final except the parked item)
- **Questions, not answers.** Each line is something to inspect this time, never a
  directional rule. A persisted answer rots into a wrong rule; a question only directs attention.
- **Own-ticker only.** Before rewriting, the learner reviews the recent PIT-visible
  own-ticker **full learner reports already surfaced by the existing prior-report
  plumbing** (same glob + PIT predicate P5 + self-leak guard P6 — **no new discovery
  path**), not just the previous checklist. Output is still ONE rolling list. Peer
  learning stays in prior_reports_context (P3) — never merged. (Window size = "N" —
  PARKED, see below.)
- **One living list, consolidated across the review window.** Learner replaces it
  whole each cycle. **Keep durable *recurring conditional* questions even when the
  condition was absent this quarter — do not drop a dormant recurring check merely
  because it didn't fire (this is the anti-forgetting fix).** Otherwise drop freely:
  refuted, generic, stale, redundant, genuinely one-off, or weaker than a sharper
  replacement. Sharpen survivors; add new.
- **Anti-generic by disqualifier, NOT by example.** The learner prompt forbids any line
  that would be true for a different company/quarter unedited, or that a generic analyst
  checklist already contains; each line must trace to how THIS prediction's reasoning
  diverged from the actual outcome. Rationale (do not "helpfully" re-add examples):
  LLMs over-anchor on few-shot exemplars, and this is a rewrite loop, so a seeded
  example becomes a self-perpetuating attractor. If any illustration is unavoidable,
  use the codebase's existing "format only — do not reuse" convention.
- **No source link in the checklist block.** The checklist is rendered directly from the
  latest allowed own-ticker learner JSON; prior-report links already appear in
  `prior_reports_context`. A separate checklist link is redundant, and per-item/block
  links would reintroduce lineage/state.
- **Shape gate only.** A list of short single-sentence strings. No semantic validator,
  no per-item review, no labels.
- **Engaged in prose.** Predictor addresses relevant items in `analysis`, dismisses the
  rest in one line. No structured `checklist_review[]` field.
- **Never evidence.** Checklist text is never a source ID. Directional calls still need
  ≥2 grounded source IDs, ≥1 from the current bundle (the other may be a prior report),
  per V2 — unchanged.

### Cross-report synthesis (ephemeral — three fences + a guardrail)
The N-report review exists only to write sharper *questions*. Prompt-level, no numeric
floor (respects the parked cap):
- **Questions only.** The synthesis may never emit a verdict/rule ("X → short"); the
  disqualifier rule applies to synthesized items too.
- **Small-sample honesty.** When own-ticker history is thin, recurring claims must be
  phrased tentatively, and each recurring item must be grounded in the specific past
  reports it generalizes from *in the learner's reasoning* — never persisted as
  per-item lineage.
- **Predictor-observability (prediction-time actionable).** The learner sees a strictly
  larger information set than the predictor (this quarter's transcript / earnings call /
  post-event analyst revisions + the actual outcome; the predictor at 8-K time sees only
  the 8-K + the prebuilt bundle and never usefully sees the current transcript). So:
  *the learner may **think** with hindsight, but every checklist item must be **answerable
  from the predictor's 8-K + bundle alone**.* Forbid lines that require the current
  quarter's transcript/call/post-event data. Insight learned from **prior** transcripts
  must be **translated into the available 8-K/bundle proxy** ("inspect X — the early tell
  that historically foreshadowed this driver"), with **outcome-neutral wording** (open
  inspection, never a leading question that telegraphs what happened). If a driver is
  genuinely transcript-only with no 8-K proxy, **do not fabricate one** — omit it, or
  frame it as a known blind-spot/data-gap caution **only when the company's own history
  supports it and only as a prediction-time check** (never a blanket "no transcript ⇒
  lower confidence" rule).

**Guardrail:** the cross-report understanding is ephemeral reasoning each cycle. Do NOT
persist a per-company "what works" / pattern profile or any new file — only
`future_checklist` persists. A stored profile = the lesson library reborn.

### Forbidden (these recreate lesson machinery)
separate checklist store · checklist IDs · per-item source lineage · scores ·
helped/misled labels · keep/drop state · predictor `checklist_review[]` · validator
completeness checks · peer/industry checklist merging · orchestrator-parsed scope/route ·
per-company "what works" / pattern profile · any stored cross-report synthesis.

### Build cost
2 prompt edits (learner: rewrite the carried list; predictor: engage it in analysis) +
orchestrator surfaces one field it already reads + enforces only the existing basic
type/shape check.
No new artifact, validator, or PIT logic.

### Effectiveness lever
Realized value is gated almost entirely by the learner distillation prompt, not the
architecture. Force ticker-specific, non-obvious, mistake-derived questions; prune
anything a competent analyst would do anyway. Prioritize this prompt above all else.

### Parked (UNRESOLVED — do not finalize without the user)
Any cap on item count and any minimum-count / minimum-evidence floor. The user is
uncomfortable with artificial caps; no number is decided. A bot must NOT hard-code one.
Also: **N** — how many prior own-ticker reports the learner reviews when consolidating —
is a placeholder in the same bucket: unresolved, no number hard-coded.

### Canonical one-liner
One rolling own-ticker standing checklist, living only inside the latest learner result
the predictor is allowed to see. The orchestrator renders it forward, the predictor
engages it in prose, the learner fully rewrites it after the outcome — consolidating
across recent PIT-visible own-ticker reports. Questions only, never evidence
(directional calls still need ≥2 grounded IDs, ≥1 from the current bundle). No separate
store, no lifecycle, no source link. Item-count cap and review-window N are parked.

---

## SKILL.md Migration Map — Predictor & Learner (2026-05-15)

> Rigorous line-level read of `.claude/skills/earnings-prediction/SKILL.md` and
> `.claude/skills/earnings-learner/SKILL.md` against the locked target state. Analysis
> only — no code/skill changes yet. This is the authoritative KEEP / CHANGE / DELETE
> map a bot follows when rewriting the two skills.

### Crux

```
Predictor skill:  analytical spine is EXCELLENT — keep it.   Lesson-labeling apparatus ≈ 40% of file = DELETE.
Learner skill:    causal-attribution spine is EXCELLENT — keep. Lesson/audit/global apparatus ≈ 60% = DELETE.
Replaces it:      prior_reports + standing-checklist surface (predictor) / checklist-rewrite (learner).
```

Nothing in the *reasoning* logic is wrong. Both files are saturated with lesson
machinery the target removes. The hard part is the **replacements for §3.3 (predictor)
and Phase 4 (learner)** — that is where the new checklist loop + fences live, and where
a bot must NOT smuggle back any lesson-shaped structure.

### earnings-prediction/SKILL.md

| Lines | What | Verdict |
|---|---|---|
| 1-13 frontmatter | `allowed-tools: Read/Write/Glob` | CHANGE — **remove the static `allowed-tools` block entirely.** Single source of truth = the orchestrator's SDK `allowed_tools` passed per invocation (M2/FIX-5; historical=Read+Bash+DataSubAgents, live=+WebFetch+Neo4j+IBKR). Leaving a static list risks it intersecting with / over-restricting the SDK set (e.g. silently breaking live mode). Do not "mark non-authoritative" — delete it. |
| 15 ultrathink | | KEEP |
| 17-21 §1 Mission | "from a prebuilt context bundle … let the bundle evidence determine … inspect everything in the bundle" + no-early-impression, no_call-first, stress both sides | KEEP the spine verbatim (no prior view / stress both / no_call if no edge / no early impression — the locked prediction criterion). **REWRITE only the bundle-confinement framing:** the target relaxes bundle-only (plan #3 + M3 historical=DataSubAgents + M4 live=web/Neo4j/IBKR). New wording = *the bundle is the **primary** substrate; mode-allowed tools may be used for **targeted** gap-fills that could change the call — under SLA, no fishing expeditions* (plan 3.1 speed). My earlier "KEEP verbatim" was wrong — the old text encodes the removed bundle-only restriction. |
| 25 §2 input paths | RENDERED/BUNDLE/AUDIT/RESULT | KEEP |
| 27-31 §2 lesson sidecars | `## Lessons To Label`, `learner_result:`, `_allowed_learner_paths`, `#S10.lesson.L<n>` | REWRITE → prior-reports surface: rendered §10 "Prior Reports", allowlist→`_allowed_prior_report_paths`, source-id `#S10.report.R<n>`, predictor opens prior `result.md`; add the standing checklist here. |
| 33 §2 related-filing sidecars | `_allowed_related_filing_paths` | KEEP — not lesson machinery (U7), independent. |
| 37-39 §3.1 | read rendered bundle | KEEP |
| 41-79 §3.2 Section Audit | facts-only §2–§9, no final call in audit | KEEP (F6) but **define the audit boundary semantically, not by section number** (consistent with the Bot-Safe "anchors, not line numbers" rule — section numbers move when the renderer changes): *audit the current-event factual sections; exclude the Prior Reports / Standing Checklist memory section.* Do not hard-code "§2–§9" / "§10". |
| 81-134 §3.3 Lesson Labeling | entire subsection | DELETE ENTIRELY → replace with short "Prior Reports & Standing Checklist" subsection (two-pass forced-recent-4 open + engage checklist as questions in prose, never evidence). |
| 138 §4 Phase 1 | quality-not-size, surprise math | KEEP |
| 140-148 §4 Phase 2 | five questions | KEEP verbatim — analytical core. |
| 150 §4 Phase 3 | stress both sides → no_call | KEEP |
| 152 §4 Phase 4 | call + data gaps | CHANGE — add locked no_call two-path (Balanced vs Missing-data, V5/FIX-6) + anti-lazy (directional ≥2 grounded IDs, ≥1 current-bundle, V1/V2). |
| 159-182 §5 schema | has `lesson_labels`, `cites_lesson_indices` | CHANGE — drop both; add `pit_mode`, `opened_prior_reports[]`. (buckets stay `finalize`-derived.) |
| 197 key_drivers def | requires `cites_lesson_indices` | CHANGE — remove; add ≥2-grounded/≥1-current-bundle rule. |
| 199 lesson_labels def | | DELETE |
| 203 evidence_ledger | SRC: catalog grounding | KEEP (#10/#22) + live accepts `SRC:LIVE:*` (V3/V4). |
| 205 analysis def | "must not quote non-confirmed lesson_text" | CHANGE — drop substring rule; add engage-checklist + explain-no_call-path. |
| 209-224 §6 Compliance | all lesson-validation items | DELETE lesson items; rewrite to: anti-lazy ≥2-grounded, no_call two-path, SRC catalog (+LIVE), opened_prior_reports recorded, checklist engaged. (evidence_ledger item stays.) |
| 227-231 Hard Rules 1-5 | sourcing, no_call, review-all, ≤30 conf, market=context+PIT | KEEP |
| 232 Hard Rule 6 | lessons inform-not-replace; key_drivers evidence non-lesson | KEEP INTENT, REWRITE wording → prior reports/checklist inform interpretation but are NEVER a source ID (bundle-primary / never-evidence). |
| 233 Hard Rule 7 | zero-lessons-confirmed + both ways → no_call | CHANGE → restate as balanced no_call rule, no lesson framing. |
| 234 Hard Rule 8 | write only 2 paths | KEEP |

### earnings-learner/SKILL.md

| Lines | What | Verdict |
|---|---|---|
| 1-7 frontmatter | "writes reusable lessons"; SDK-embed note | CHANGE desc wording (causal report + checklist). KEEP SDK-embed/main-session (E1). |
| 11-13 Goal/Thinking | "write reusable lessons" | CHANGE goal wording; KEEP ultrathink/deep-causal. |
| 21-34 Inputs | `PRIOR_LESSONS` → ticker.json | CHANGE — delete PRIOR_LESSONS; add the carried standing checklist + the recent N PIT-visible own-ticker reports **made available by the existing prior-report plumbing (same glob + PIT predicate P5 + self-leak guard P6 — no new discovery path)**. KEEP pit_*, prediction/bundle/actual_return. |
| 40-61 Output schema | `attribution_result.v3`; global_observations; lesson_audit; predictor_lessons; data_lessons | CHANGE schema→`learner_result.v1` (S3; reconcile known v2/v3 contradiction). DELETE global_observations, lesson_audit, predictor_lessons, data_lessons. ADD `key_takeaway` + `future_checklist[]`. KEEP evidence_ledger, primary_driver, contributing_factors, missing_inputs, refs. |
| 63-73 Feedback block | predictor_lessons, data_lessons rows | CHANGE — drop those 2 rows; KEEP prediction_comparison (EV1 metrics), what_worked, what_failed, why. |
| 74-80 Evidence rules | ledger discipline | KEEP; drop the predictor_lessons/global/audit evidence_refs clause. |
| 82-124 Structured lesson output v3 | full lesson schema/rubric | DELETE ENTIRELY → replace with the `future_checklist` authoring contract (questions-only · anti-generic-by-disqualifier · prediction-time-actionable · small-sample honesty · keep-durable-conditionals/drop-freely · no stored profile). |
| 126-186 Lesson audit v3 | entire | DELETE ENTIRELY |
| 187-189 Category field | primary_driver.category | KEEP — useful causal tag, lesson-independent. |
| 191-261 Global observations | scope/sector enums, shapes | DELETE ENTIRELY |
| 266-277 Phase 1 | read prediction; scan bundle for what predictor could see; note actual | KEEP 1-2-4 (step 2 = the observability boundary, gates the prediction-time-actionable fence). Step 3 PRIOR_LESSONS→carried checklist+N reports. DELETE step 5 (lesson labels). |
| 278-298 Phase 2 Investigate | DataSubAgents, PIT tiers, transcript/XBRL/news/peers | KEEP fully — the richer info set (incl. this-quarter transcript) that makes the checklist valuable and creates the asymmetry the observability fence governs. |
| 300-304 Phase 3 Attribute | primary/contributing/comparison | KEEP |
| 306-322 Phase 4 Distill Lessons | three-scope probe, steps 9-12 | REWRITE → "Rewrite the standing checklist": consolidate carried checklist + last N own-ticker reports + this prediction + outcome, apply all fences, emit key_takeaway + future_checklist. Delete steps 9-12. |
| 323-328 Phase 5 Finalize | missing_inputs, sources, one file | KEEP |
| 331-344 Critical Rules | 1 generalizability(GOOD/BAD ex), 2 causal, 3 evidence, 4 caps, 5 PIT, 6 one-file, 7 daily_stock canonical, 8 exhaust, 9 mechanism, 10 audit-honestly, 11 ground-in-quarter | KEEP 2,3,5,7,8. CHANGE 1 (reframe to disqualifier, DROP the hardcoded GOOD/BAD exemplar — anti-anchoring), 4 (drop lesson/global caps; **only `what_worked ≤ 2 / what_failed ≤ 3 / contributing_factors ≤ 3` survive — `future_checklist` gets NO numeric cap; a bot must not cap-by-analogy "predictor_lessons ≤ 3 → future_checklist ≤ 3"; the count is PARKED**), 6 (drop ticker.json/global.json mention), 9 & 11 (reframe to causal-report + checklist fences). DELETE 10 (audit gone). |

### Best target workflow (end-state)

**PREDICTOR**
1. Orchestrator passes mode-gated tools + paths. Read `RENDERED_BUNDLE` end-to-end (JSON only for exact decimals).
2. Section Audit — current-event factual sections only; exclude the Prior Reports / Standing Checklist memory section (semantic boundary, not a hard-coded section number) → `SECTION_AUDIT_PATH`.
3. Prior reports + standing checklist: fully open recent-4 own-ticker (force), summary-first older own-ticker, ≤3 peers by relevance → record `opened_prior_reports[]`. Read checklist as *questions to inspect*; engage relevant ones against the current bundle in `analysis`, dismiss the rest in one line. Never a source ID.
4. Decide: Phase 1 key numbers (quality) → Phase 2 five questions → Phase 3 stress both sides → Phase 4 call.
5. Hard contract: directional ⇒ ≥2 grounded source IDs, ≥1 current-bundle (other may be allowed prior-report; live also `SRC:LIVE:*`). `no_call` ⇒ Balanced (≥2 drivers both directions, each evidenced) OR Missing-data (≥1 `data_gap` + analysis explains; no fabricated drivers).
6. Write `RESULT_PATH` (direction, confidence, `[low,high]`, key_drivers, data_gaps, `opened_prior_reports`, `pit_mode`, evidence_ledger, analysis). Stop. Live SLA enforced by orchestrator.

**LEARNER**
1. Load: prediction/result.json; scan context_bundle to fix the observability boundary (what the predictor could see); the carried checklist; the recent N PIT-visible own-ticker reports (via the existing prior-report plumbing — no new discovery path); actual_return.
2. Investigate (Phase 2 unchanged): post-event evidence via DataSubAgents incl. this-quarter transcript/XBRL/news/peers.
3. Attribute: primary_driver (mechanism), contributing_factors, prediction_comparison (signed magnitude_error, direction_correct), what_worked / what_failed / why.
4. Rewrite the standing checklist: consolidate {carried checklist + last N own-ticker reports + this prediction + known outcome} → apply every fence (questions-only · anti-generic disqualifier · prediction-time-actionable: answerable from 8-K+bundle, translate prior-transcript insight to the available proxy, outcome-neutral, no fabricated proxy, company-history-grounded blind-spot only · small-sample honesty · keep durable recurring conditionals else drop freely · ephemeral, no stored profile) → emit `key_takeaway` + `future_checklist`.
5. Finalize: missing_inputs, data_sources_used, write `learner_result.v1` to `RESULT_PATH` only.

### Why this maximizes the two end-goals

- **Predictor accuracy** — the proven analytical spine (Mission, five-questions, stress-both-sides, evidence-ledger, PIT) is preserved untouched; lesson-labeling cognitive tax removed; hard-block validator forces grounded calls / honest no_call.
- **Useful actionable feedback** — the learner's richer post-event view (esp. this-quarter transcript the predictor never sees) is distilled, through the fences, into prediction-time-actionable questions, self-corrected each cycle by the rewrite loop, protected from forgetting by N-report consolidation.

### Top implementation risks (carry into the blueprint)

1. The §3.3 / Phase-4 replacements must not smuggle back any lesson-shaped structure (no per-item labels, IDs, audit, scope routing).
2. The learner-prompt quality gates the whole feature's value — prioritize it above all else.

---

## Borrow Review — Compressed (2026-05-15)

Reviewed the Anthropic financial-services plugins, `knowledge-work-plugins/finance`,
Claude cookbook finance/custom-skill examples, and the `research_agent` SDK example.
Raw per-repo notes were intentionally collapsed: no source introduced new architecture,
schema, or lesson machinery. Only the operative five-principle synthesis below survives.

---

## Borrow Synthesis — FINAL & OPERATIVE

> This section is what the implementer follows. The raw borrow sweep compressed to
> **5 principles**; the per-source notes were removed to avoid prompt/design clutter.
> Keeping raw items would be *net-negative*: attention quality is the #1 driver of
> prediction accuracy (locked criterion). Independently converged by Claude +
> ChatGPT (no open disagreement).

**The 5 (ranked by leverage):**

1. **Deterministic numeric truth** *(order-of-magnitude — a BUILD, not prompt text).*
   Scripts (never the LLM) compute direction-correct, signed-midpoint error,
   Brier/calibration, EV1 aggregates, tie-outs; the LLM authors **zero** numbers it
   could be graded on (learner = prose/why only). Run on a **frozen, representative +
   edge** replay set that cannot be re-picked; report **systematic bias** (mean signed
   error, hit-rate by direction, calibration-by-bucket). This is the EV1 scorer spec;
   it creates a trustworthy eval where today there is none.
2. **Falsifiable call** *(order-of-magnitude — prompt).* Predictor names the one thing
   that would break the thesis; learner objectively checks whether it fired. The same
   prose kill-condition is the live thesis-break guardrail for the post-trigger LLM
   executioner during the next 24 hours; do not create a new schema field for it.
   ≤1 clause in predictor `analysis` + ≤1 in learner attribution.
3. **Prediction-time-actionable learning** *(high — prompt).* Learner may reason with
   richer post-event evidence (esp. transcript Q&A / dodged answers — its info edge)
   but every future checklist item must be answerable from the next predictor's allowed
   bundle. ≤1 learner clause (observability fence already locked; net-new = the active
   Q&A-mining instruction).
4. **Whole-move attribution** *(high — prompt).* Learner explains the full realized
   move (durable vs one-time vs positioning as *guidance*, not a forced taxonomy),
   names offsets not just the biggest driver, no circular filler, quantify only where
   genuinely sourced, and **flags the unexplained residual** → that residual becomes
   the next checklist question. ≤1 learner clause.
5. **Metric-first reasoning** *(solid & mandatory, NOT transformative — prompt).*
   Before any call, name the few metrics THIS ticker's market actually grades on;
   reject any signal — own-metric emphasis OR peer read-through — that doesn't map to
   that mechanism. Reorder/sharpen the existing Phase-2 clause to step-1; derive,
   never hardcode.

**Integration rule (binding):** weave principles 2–5 as **terse single clauses into
the existing SKILL phases — NO new "Principles" block, no schema, no machinery** (total
SKILL growth ≈ 5–8 lines). Principle 1 is the EV1 scorer script/build, NOT prompt text
— it never touches predictor/learner prompts.

**Discard (do not reintroduce):** standalone source-specific borrow items; forced
taxonomies; peer-read taxonomies; telemetry/token instrumentation as a design
principle; warning/suggestion taxonomy; ALL hardcoded examples, benchmark tables,
thresholds. Everything from the sweep either folds into the 5 or is dropped.

---

## Execution-billing Option #6 — Scripted Interactive REPL (subscription path)

> Scope note: this documents **only Option #6**. Full options matrix, empirical proof,
> billing mechanics, and the apply-this-fix recipe are canonical in
> **`.claude/plans/ANTHROPIC_BILLING_SUBSCRIPTION_CRITICAL.md`** — read that before any
> SDK/entrypoint change. (Effective 2026-06-15, programmatic `claude_agent_sdk` /
> `claude -p` left the general subscription; this option is the only proven way to keep
> the automated earnings/guidance work billing as **subscription**.)

**What it is.** Run the predictor/learner/guidance work as skills/slash-commands inside
a **real interactive Claude REPL** — launched programmatically via `pty.fork()`, with
**no `-p` and no `--print` anywhere** — so the process starts with
`CLAUDE_CODE_ENTRYPOINT=cli`.

**Why it bills as subscription.** Billing is decided solely by the non-spoofable
`CLAUDE_CODE_ENTRYPOINT` tag set at process start: interactive (no `-p`) ⇒ `cli` ⇒
**subscription quota** (5h/weekly limits, recently raised); `claude -p` / SDK ⇒
`sdk-cli` ⇒ the separate June-15 programmatic pool. A scripted `pty.fork()` REPL with
no human present still tags `cli` (empirically proven, test #11) → automated **and**
subscription-billed.

**Caveats (empirically observed).** TUI keystroke automation is fragile
(BypassPermissions dialog, render collapse, `EAGAIN`, nested-TUI). **Anthropic is
actively building detection for automated interactive use; the documented consequence
if detected is suspension/ban of the *entire Claude subscription* — all Claude access
(this pipeline + Claude Code), not just earnings/guidance.** Mitigation shape if ever
built: the **sentinel-file PTY driver** (poll for `result.json`, never screen-scrape)
— see the PRELIMINARY section of the canonical doc.

**Verdict. Reference-only — NOT the path.** The documented default is **Option 1**
(SDK + key-strip + fail-closed + overage `org_level_disabled`; volume handled by
batching, or Codex/ChatGPT for heavy batches). Option #6 is the **most code, least
durable** option and adds Claude-subscription-suspension risk; build only on an
explicit, owner-approved decision. Full scope + effort + Open-decisions:
`.claude/plans/ANTHROPIC_BILLING_SUBSCRIPTION_CRITICAL.md` (PRELIMINARY section).
