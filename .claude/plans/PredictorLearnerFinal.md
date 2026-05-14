
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

1. **[PARTIAL] Anti-lazy in prompt, not validator.** Q1 FCX-style lazy directional calls are prevented by an explicit predictor workflow step requiring ≥2 cited bundle facts for any non-`no_call` call. Validator stays shape-only; semantic checks reserved for hard violations. Current: `.claude/skills/earnings-prediction/SKILL.md:232` says every `key_drivers[i].evidence` must be non-lesson-grounded, but no explicit ≥2 minimum; tighten to ≥2.

2. **[ALREADY] MSE uses `expected_move_range_pct` midpoint.** The current predictor already emits `[low, high]` at `.claude/skills/earnings-prediction/SKILL.md:195`; backtest MSE compares actual_pct to range midpoint. No per-lesson magnitude buckets needed.

3. **[PARTIAL] Locked summary fields in `learning/result.json`.** Two NEW fields to add: `key_takeaway` (1 sentence) + `future_checklist[]` (things to check next time). Tags were considered and DROPPED (FIX-8 — no consumer). Orchestrator reads these from the JSON file directly (not from `.md`) for the summary shown to the next predictor. Current learner already emits `primary_driver` + `feedback{what_worked, what_failed}`.

4. **[NEW] Speed via injection + tiered SLA (LIVE only).** Inject `time_since_release` every turn (or one-shot at kickoff + enforce hard timeout) so predictor sees elapsed time. **Live SLA (per FIX-10):** 90s soft warn / 120s ship-the-call / 300s hard kill. Historical mode keeps a softer budget with no hard kill.

5. **[PARTIAL] Mode-aware tool gating, single skill.** One skill with `mode={historical, live}`; historical exposes DataSubAgents only (PIT-safe), live exposes full tools (web, neo4j, IBKR, MCP). Avoids two divergent skill files. Current: `pit_mode` field already exists in learner output (`historical`/`live`); skill does not yet gate tools by mode — add gating.

6. **[ALREADY] No learner-AUTHORED YAML; renderer metadata frontmatter OK.** Learner writes `learning/result.json` only — no YAML hand-authored anywhere. The `.md` file's existing autogenerated frontmatter (`autogenerated: true`, `source: result.json`, `generator: ...`) is renderer metadata and stays. Orchestrator never parses `.md` for content.

7. **[NEW] Wipe FCX corpus.** Stale, file inconsistencies, only Q3 usable; regeneration under new design is cheaper than preservation.

8. **[NEW] Sector/macro sub-agents deferred.** Copy the existing DataSubAgents pattern when the first prediction proves the need; not a blocker for shipping the new predictor/learner.

9. **[NEW] Historical + live ship together.** Both modes ship in the same release; mode flag gates tools, skill workflow is shared. Do not stage live for later.

10. **[ALREADY] Keep `evidence_source_catalog`.** `SRC:TICKER:QUARTER:ACCESSION#location` IDs in `key_drivers[].evidence` ground every cited fact at `.claude/skills/earnings-prediction/SKILL.md:203`, independent of lessons. Citation grounding survives the lesson removal.

11. **[NEW] Context bloat ignored on cost grounds.** Claude Code Max absorbs the dollar cost; cost is not a reason to cap report count. Attention quality IS a reason to cap (see #19).

12. **[ALREADY] `learning/result.json` is the only structured surface.** Confirms #6 from a different angle: the JSON file is the canonical structured artifact; `.md` is auto-rendered from it (with minimal autogen frontmatter as renderer metadata only). Nothing else is structured anywhere in the report.

13. **[PARTIAL] Tiered reading discipline for linked reports (per FIX-7).** Skill enforces: (1) MUST fully open the most-recent 4 own-ticker reports. (2) Older own-ticker reports (positions 5–8) are summary-first; open only if takeaway/setup suggests relevance. (3) May open up to 3 of the 4 visible peer reports based on summary. (4) Must record opened reports in JSON (`opened_prior_reports[]` per S1). Current code: predictor skill Phase 1-4 workflow + `learner_result:` link allowlist exist, but reading is OPTIONAL today — make tiered reading the contract.

---

## Borrowed from ChatGPT review (2026-05-12)

14. **[PARTIAL] Anti-lazy applies to ALL directional calls, no confidence threshold.** Q1 FCX was confidence 48 with direction `short` and still lazy — any threshold (≥60) would have missed it. Rule: `direction in {long, short}` requires ≥2 cited bundle facts, regardless of confidence. Same scope as #1 — bundle the wording fix with #1.

15. **[ALREADY] Preserve existing JSON-canonical, .md-rendered pattern.** Already in code: learner writes `learning/result.json`; `scripts/earnings/result_md_renderer.py` produces `learning/result.md` from it. Keep this pattern in the new design — orchestrator reads JSON directly, never parses `.md`. ChatGPT framed this as a borrowed idea but it's the current pattern; just don't accidentally regress to markdown-with-embedded-JSON.

16. **[ALREADY] Richer learner JSON schema.** Current learner schema is already RICHER than ChatGPT proposed: `primary_driver`, `contributing_factors`, `feedback{what_worked, what_failed}`, `global_observations`, `missing_inputs`, `evidence_ledger`, `lesson_audit`. Keep this surface; just drop `lesson_audit` (lessons gone) and consider adding `future_checklist[]` for the next predictor (see #20 for naming).

17. **[NEW] Tiered SLA for LIVE mode only (per FIX-10).** Live SLA: 90s soft warn (warning injected) / 120s operating target (predictor MUST ship best-available call unless actively resolving material uncertainty) / 300s hard kill (orchestrator force-terminates; writes timeout no_call fallback). Historical mode keeps soft cap with no hard kill.

---

## Second-round borrows from ChatGPT review (2026-05-12)

18. **[PARTIAL] Signed midpoint for MSE.** Current `expected_move_range_pct` is positive-only; for MSE compute signed = sign(direction) × midpoint(range), then compare to signed actual_pct. Refines item #2.

19. **[NEW] Cap prior-report count for attention quality (per FIX-7).** Cap at **12 visible prior reports** per prediction: 8 own-ticker + 4 industry-peer. Forced-open only the most-recent 4 own-ticker; older are summary-first. May open up to 3 peers based on relevance. Refines item #11.

20. **[NEW] Rename "what_to_check_next_time" → "future_checklist".** Shorter, clearer, implies the field gets used as an actual checklist by the next predictor. Refines items #3 and #16.

21. **[NEW] Predictor selects which linked reports to open.** Two-pass: first see linked-report metadata (date, ticker, 1-line summary), then pick N to open fully. Avoids forced reading of irrelevant reports. Refines item #13.

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
- **Simplify prediction validator.** Keep schema/metadata/range/evidence-source validation; remove formal lesson-label validation; add only the small directional anti-lazy shape rule: `long`/`short` needs >=2 grounded key drivers.
- **Simplify learner validator.** Keep actual return, evidence ledger, primary/contributing drivers, prediction comparison, missing inputs, data sources, refs; remove structured lesson/global-observation routing rules.
- **Make `learning/result.json` the only memory source.** Add `key_takeaway` (1 sentence) + `future_checklist[]`. Tags considered and DROPPED (FIX-8 — no consumer). Orchestrator scans prior event `learning/result.json` files and renders links/summaries for the next predictor.
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
- **`_allowed_learner_paths` IS the existing PIT-safe prior-report FILE allowlist.** Defined at `orchestrator.py:2093`, consumed at `renderer/lessons.py:195`, invariant-checked at `orchestrator.py:1709-1758`. Rename to `_allowed_prior_report_paths` and reuse for the prior-report `.md` file allowlist. NOTE: this mechanism only covers file-path allowlisting; it does NOT solve live web/IBKR/Neo4j/MCP tool gating, which needs a separate runtime `mode` config (see item #5).
- **Delete `_text_utils.py` (79 lines), but only AFTER removing all callsites.** Contains `_normalize_lesson_text` and `iter_labeled_lessons`. Imports to drop: `orchestrator.py:337, 641, 2815, 2817`. CRITICAL — `_normalize_lesson_text` is also CALLED at 8 sites inside orchestrator.py: 790, 830, 834 (inside `validate_prediction_result`), 1846, 1847 (inside `_content_matches`), 2846, 2847 (inside `aggregate_lesson_audits`), 3043, 3044 (inside `_validate_audit_against_prediction`). The 5 callsites at 1846–3044 disappear when their containing functions are deleted; the 3 callsites at 790/830/834 must be removed as part of the `validate_prediction_result` simplification (see Validator preservation item below). `validate_learning.py` has zero `_text_utils` refs.
- **`renderer/__init__.py` cleanup.** Remove `from .lessons import _render_learning_context` (line 17) and the matching entry in `__all__`. Add export for new `_render_prior_reports`.
- **20 orchestrator functions to REMOVE outright between lines 1463–2767 (~1200 lines).** `_stamp_ticker_lesson_row` (1463), `append_ticker_lesson` (1487), `append_global_lessons` (1563), `_assert_learner_paths_invariant` (1700) — replace with a smaller prior-report invariant check, `DuplicateLessonIdError` (1776), `_routing_key_from_source` (1790), `compute_lesson_id` (1817), `_content_matches` (1840), `assert_no_id_collision` (1862), `compute_status` (1900), `_passes_audit_pit` (1961), `_apply_render_view` (1986), `_stamp_quarter_row_skeleton` (2445), `_upsert_audit_in_history` (2473), `_apply_audit_ticker` (2491), `_apply_audit_global` (2533), `_apply_audit_and_append_global_atomic` (2565), `_append_lesson_row_to_ticker_quarter` (2614), `_register_replacement` (2670), `aggregate_lesson_audits` (2767). PLUS `_validate_audit_against_prediction` (orchestrator part 2, line 2968) — also lesson-bound (asserts `lesson_audit` count == `lesson_labels` count, imports `iter_labeled_lessons`) and called from `run_learner_for_quarter` (1248, 1261) and `_full_validate_for_orchestrator` (3098). DELETE it AND its two callsites.
- **REWRITE not delete: `build_learning_context` (2101) → `build_prior_reports_context`.** Replace lesson-loading body with prior-report selection; reuse PIT-filter logic and `_allowed_learner_paths` plumbing.
- **REWRITE not delete: `_decorate_with_learner_paths` (2030).** Keep PIT self-guard (lines 2055–2065) and allowlist assembly (Phase 2); change per-entry attachment from lessons to prior-report summary rows.
- **Hook `validate_learning_output.py` (`.claude/hooks/`) STAYS.** Wrapper logic untouched; the imported `validate_attribution_result` function name is preserved across the rewrite. Path-matcher (`endswith("/learning/result.json")`) is correct.
- **Schema-version bumps + their write sites.** `prediction_result.v1` → bump if adding mode/anti-lazy fields; update `orchestrator.py:701, 3510`. `attribution_result.v3` → `learner_result.v1`; update `validate_learning.py:133, 135` and the docstring refs at `result_md_renderer.py:218, 483`. `ticker_lessons.v2` / `global_lessons.v2` constants: delete with their files. ALSO update: `.claude/skills/earnings-learner/SKILL.md` (carries the schema string in examples), `scripts/earnings/tests/fixtures/learner_session.jsonl` (fixture contains schema_version), prediction skill SKILL.md output example, any renderer-docstring references, validator error messages that name the schema string, and any frozen test JSON fixtures.
- **Quantified churn (ESTIMATES — confirm per-file during implementation).** Orchestrator: ~1200 lines removed (out of 4063); ~391 lesson-mentioning lines. `validate_learning.py`: rewrite (616 → ~200 lines). `renderer/lessons.py` + `_text_utils.py`: delete (377 lines). **Tests:** ~12 files delete entirely (~1100 lines), ~14 files rewrite/trim. **Goldens:** ~22 of 66 regenerate. These counts came from grep heuristics; the exact split (delete vs trim) for each file needs per-file triage before committing to a number.
- **Predictor SKILL.md surgical map.** Delete §3.3 (lines 81–128) entirely. Strip `lesson_labels`, `cites_lesson_indices` from §5 example + field defs. Delete line 114 (Citation rule), line 116 (analysis substring rule), line 197 (cites_lesson_indices in key_drivers def), line 232 ("lessons inform interpretation"). Rewrite lines 27–31 (replace `S10.lesson.L<n>` source-ID pattern with `S10.report.R<n>`).
- **Learner SKILL.md surgical map.** Delete §Structured lesson output v3 (82–125), §Lesson audit v3 (126–186), §Global observations (191–263), §Phase 4 Distill Lessons (306–322). Rewrite §Feedback block table (63–73) to drop predictor_lessons/data_lessons rows. Add `key_takeaway` (1 sentence) + `future_checklist[]`. Tags dropped per FIX-8.
- **Predictor prompt builders (`orchestrator.py` part 2).** `_build_predictor_prompt` (line 833 part 2): **no lesson logic inside this function** — verified it only passes path env vars (`BUNDLE_PATH`, `RENDERED_BUNDLE_PATH`, `SECTION_AUDIT_PATH`, `RESULT_PATH`). The lesson surface that flows to the predictor lives in the rendered bundle (`renderer/lessons.py` output) + the predictor SKILL.md prompt itself; removing those upstream surfaces is sufficient. `_build_learner_prompt` (351): verify lesson-section instructions and strip if present. `_load_learner_skill_content` (340): no code change — reads the rewritten learner SKILL.md.
- **Builders directory is CLEAN (verified).** Zero lesson references across all 8 builder files (`adapters.py`, `consensus.py`, `eight_k_packet.py`, `guidance_history.py`, `inter_quarter_context.py`, `macro_snapshot.py`, `peer_earnings_snapshot.py`, `prior_financials.py`). No changes needed.
- **Non-lesson renderer files CLEAN (verified).** Zero lesson references in `consensus.py`, `financials.py`, `_formatters.py`, `guidance.py`, `header.py`, `inter_quarter.py`, `macro.py`, `peers.py`, `results.py`. Only `bundle.py` (4 refs) and `__init__.py` (2 refs) need edits.
- **`run_ledger.py` CLEAN (verified).** Zero lesson references. Unchanged.
- **`_atomic_write_json` (`orchestrator.py:1444`) STAYS.** Used by prediction finalize + result.json writes outside the lesson surface.
- **Validator preservation.** `validate_prediction_result` (`orchestrator.py:658`): KEEP U67 `evidence_source_catalog` grounding (lines 853+) — that's the citation anchor that survives. REMOVE: (a) `lesson_labels` from `REQUIRED_KEYS` list (line 692), (b) the full `lesson_labels` validation block (lines 744–795), (c) `expected_lesson_texts` kwarg (line 662), (d) the `cites_lesson_indices` block, (e) the `analysis` substring rule that bans verbatim non-confirmed lesson_text (~line 832 area), (f) the `_normalize_lesson_text` import at line 337.

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
**Answer:** (a) STANDARD — drop lesson_labels + cites_lesson_indices; KEEP magnitude_bucket + confidence_bucket; ADD `opened_prior_reports[]` + `mode`.
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
**Answer:** (a) Filesystem glob — walk `earnings-analysis/Companies/*/events/*/learning/result.json` at bundle-build time. Log + skip on missing/invalid.
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
  2. If `prediction/result.json` is missing or invalid → orchestrator writes a VALID live no_call fallback: `{direction: "no_call", confidence_score: 0, expected_move_range_pct: [0, 0], mode: "live", data_gaps: ["live_timeout"], opened_prior_reports: [<whatever was logged before kill>], analysis: "Hard timeout at 300s — no valid prediction written before kill."}` plus `timeout=true` metadata.
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
