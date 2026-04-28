 Plan — Wire learner_result Paths Into Bundle (JSON + Rendered) + PIT Allowlist

 Status: Approved, ready to execute
 Owner of this slice: scoped extraction from the larger earningsBundleRenderer.md audit
 Plan file: this document
 Mode: TDD — failing tests first, then implementation, then verify

 ---
 1. Context (why)

 The predictor reads RENDERED_BUNDLE_PATH as its primary surface and may dip into BUNDLE_PATH for verification. The
 lessons section currently surfaces only the text of prior-quarter lessons — never a way back to the full prior
 learner report (learning/result.md) that produced those lessons. As a result, the predictor can't follow the chain of
  provenance: when a lesson body alone isn't enough to decide a confirmed/contradicted/irrelevant label or to ground a
  key driver, it has no path forward.

 This change: every prior-quarter lesson the bundle exposes also carries an inline pointer to its source
 learning/result.md, on both surfaces (JSON + rendered). A top-level allowlist (_allowed_learner_paths) is the
 canonical PIT-safe set the predictor is permitted to Read; the renderer also surfaces this allowlist as a labeled
 block. SKILL.md is updated minimally so the predictor knows the affordance exists, when to use it, and the
 cross-surface invariant.

 Why PIT-safe: every lesson's underlying result.md was authored by the learner of a prior event whose own PIT cutoff ≤
  the predictor's PIT cutoff; the existing source_pit_cutoff filter already strips lessons whose cutoff exceeds the
 predictor's. The current-quarter guard is a defensive belt-and-suspenders against stale re-runs in live mode.

 Out-of-scope: the broader ## Lessons To Label / ## Context-Only restructure in earningsBundleRenderer.md §1.10;
 orchestrator predictor-prompt update (§3); validator allowlist on evidence_ledger[].source (Decision 5 — confirmed
 moot per validator audit below).

 ---
 2. Validator audit (D8(ii) closeout)

 Three places touch evidence_ledger:

 - scripts/earnings/earnings_orchestrator.py::validate_prediction_result (L382–564): only check is L459 — for key in
 ("key_drivers", "data_gaps", "evidence_ledger"): isinstance check. No iteration of entries, no source inspection, no
 enum, no prefix list, no regex.
 - scripts/earnings/validate_learning.py::validate_attribution_result (L134–149): different schema entirely ({id,
 claim, value, source, date}); requires source key presence, never inspects content.
 - .claude/hooks/: zero references to evidence_ledger.

 Conclusion: there is no existing allowlist on evidence_ledger[].source. The plan's Decision 5 ("validator allowlist
 extends to accept this prefix") describes future work and is not blocking. No validator changes shipped here. The
 source: "learner_file:<path>" convention is taught via SKILL.md only — soft contract, traceability-only.

 ---
 3. Locked decisions

 #: D1
 Decision: Add per-lesson + top-level fields to learning_context JSON
 Resolution: APPROVED — sanctioned scoped deviation from earningsBundleRenderer.md §"Out of scope"
 ────────────────────────────────────────
 #: D2
 Decision: Field naming
 Resolution: JSON: learner_result_path (per lesson) + _allowed_learner_paths (top-level). Rendered: learner_result:
   (line marker)
 ────────────────────────────────────────
 #: D3
 Decision: Decoration site
 Resolution: At read-time inside build_learning_context. Storage files (learnings/ticker/*.json,
 learnings/global.json)
   untouched
 ────────────────────────────────────────
 #: D4
 Decision: Path format
 Resolution: Repo-relative (earnings-analysis/Companies/{TICKER}/events/{Q}/learning/result.md)
 ────────────────────────────────────────
 #: D5
 Decision: PIT guard
 Resolution: Inside build_learning_context only via new current_quarter_label kwarg; renderer signature unchanged
 ────────────────────────────────────────
 #: D6
 Decision: Missing file
 Resolution: Stat-check; omit key entirely — never write null, never write a placeholder
 ────────────────────────────────────────
 #: D7
 Decision: Rendered placement
 Resolution: Per-ticker-quarter block: one line as last sub-bullet, before blank separator. Per-global-lesson: one
   continuation line under each scope bullet. Path is per-source-event, not per-text-bullet
 ────────────────────────────────────────
 #: D8
 Decision: SKILL.md
 Resolution: IN-SCOPE; minimal additive insert at end of ## Input (between L23 and ## Rules); 3 paragraphs (paragraph
 2
   reworded per user's wording fix)
 ────────────────────────────────────────
 #: D9
 Decision: TDD order
 Resolution: Builder tests (16) → renderer tests (6) → cross-surface equivalence (1) → implementation → smoke
 ────────────────────────────────────────
 #: D10
 Decision: ticker_ref / global_ref
 Resolution: UNCHANGED — out of scope
 ────────────────────────────────────────
 #: Q1
 Decision: Allowlist key location
 Resolution: bundle["learning_context"]["_allowed_learner_paths"] (sibling of ticker_ref/global_ref)
 ────────────────────────────────────────
 #: Q2
 Decision: Allowlist ordering
 Resolution: Render-order (ticker_lessons recency-desc, then sector→macro→cross_ticker globals; matches inline
   learner_result: ordering)
 ────────────────────────────────────────
 #: Q3
 Decision: Empty allowlist
 Resolution: Skip the entire "### Allowed learner reports for this prediction" block (no heading, no empty list)
 ────────────────────────────────────────
 #: Q4
 Decision: Self-check invariant
 Resolution: raise AssertionError(...) (NOT bare assert — survives python -O)
 ────────────────────────────────────────
 #: Q4-extra
 Decision: Production call site
 Resolution: Orchestrator MUST always pass non-None current_quarter_label; builder default None is a safety hatch for
   ad-hoc/diagnostic callers
 ────────────────────────────────────────
 #: Q5
 Decision: Block placement
 Resolution: Immediately after ## Prior Lessons (from learner), BEFORE ### Ticker Lessons
 ────────────────────────────────────────
 #: Q6
 Decision: Empty-context behaviour
 Resolution: UNCHANGED — when both ticker_lessons and global_lessons are empty, renderer emits the existing "No prior
   lessons available (first prediction for this ticker)." message and returns (text, []). The R1 byte-equality test
   continues to pass; the allowlist block is omitted by Q3 (empty list ⇒ skip)
 ────────────────────────────────────────
 #: Q7
 Decision: Test isolation
 Resolution: Pure unittest + tempfile.TemporaryDirectory() in setUp/tearDown (matches existing
   test_learning_context.py style; no pytest fixtures). New kwarg companies_dir: Path | None = None mirrors
   existing base_dir plumbing pattern (orchestrator L1218). See §6.1 for full details

 ---
 4. Files touched

 4.1 Modified

 ┌──────────────────────────────────────────────────┬──────────────────────────────────────────────────────────────┐
 │                       Path                       │                         What changes                         │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
 │                                                  │ build_learning_context signature + body (decoration +        │
 │ scripts/earnings/earnings_orchestrator.py        │ allowlist + invariant); build_prediction_bundle call-site    │
 │                                                  │ (passes current_quarter_label)                               │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
 │ scripts/earnings/renderer/lessons.py             │ _render_learning_context body (allowlist block + per-lesson  │
 │                                                  │ learner_result: lines); signature unchanged                  │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
 │ .claude/skills/earnings-prediction/SKILL.md      │ Insert 3 paragraphs at end of ## Input section (between L23  │
 │                                                  │ and L25)                                                     │
 ├──────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
 │ scripts/earnings/test_render_learning_context.py │ Append R5 / R5b / R6 / R7 + 2 allowlist tests (6 new cases)  │
 └──────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────┘

 4.2 Created

 ┌───────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┐
 │                         Path                          │                         Purpose                         │
 ├───────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
 │                                                       │ New test file: 16 builder cases (path attach + render-  │
 │ scripts/earnings/test_build_learning_context_paths.py │ guard, missing-file, allowlist build, invariant raise   │
 │                                                       │ [+ paired positive-path], orchestrator call-site        │
 │                                                       │ assertion)                                              │
 ├───────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
 │                                                       │ New test file: 1 cross-surface equivalence test (set    │
 │ scripts/earnings/test_learner_paths_cross_surface.py  │ equality between JSON _allowed_learner_paths and        │
 │                                                       │ rendered allowlist block contents)                      │
 └───────────────────────────────────────────────────────┴─────────────────────────────────────────────────────────┘

 4.3 Untouched (verified backward-compat)

 - scripts/earnings/tests/fixtures/golden_bundles/*.json (4 files)
 - scripts/earnings/tests/fixtures/golden_renders/full/*.txt + *.sha256 (4+4)
 - scripts/earnings/tests/fixtures/golden_renders/sections/lessons/*.txt + *.json (4+4)
 - scripts/earnings/test_renderer_golden_full.py
 - scripts/earnings/test_renderer_golden_sections.py
 - scripts/earnings/test_learning_context.py (24+ existing builder tests — all use base_dir=self.tmp and pass None for
  the new kwarg by default)
 - scripts/earnings/compare_section.py, scripts/earnings/render_section.py — diagnostic callers; default-None for
 current_quarter_label keeps them working without source change. NOT touched in this slice.
 - validate_prediction_result, validate_learning.py, all hooks — moot per §2.

 Why goldens are untouched: existing golden_bundles/*.json files lack the new keys (learner_result_path,
 _allowed_learner_paths). The renderer is fully backward-compatible — when keys are absent, dict.get(...) returns
 None, the per-lesson line is skipped, and the allowlist block is omitted (Q3). Rendered output is byte-identical →
 existing goldens pass unchanged. New behaviour is fully covered by unit tests + smoke.

 ---
 5. Implementation specs

 5.1 scripts/earnings/earnings_orchestrator.py::build_learning_context

 Current signature (L1217–1219):
 def build_learning_context(ticker: str, sector: str | None = None,
                            base_dir: Path | None = None,
                            pit_cutoff: str | None = None) -> dict:

 New signature (additive, with `*` enforcing keyword-only on the new params per Fix #4):
 def build_learning_context(ticker: str, sector: str | None = None,
                            base_dir: Path | None = None,
                            pit_cutoff: str | None = None,
                            *,
                            current_quarter_label: str | None = None,
                            companies_dir: Path | None = None) -> dict:

 Both new kwargs default to None for backward-compat AND are forced keyword-only by the `*` separator — prevents
 future positional-arg accidents on the new params. Verified non-breaking: all four current callers use kwargs
 (earnings_orchestrator.py:240, compare_section.py:80, render_section.py:55, all 24+ test_learning_context.py
 calls). companies_dir overrides the module-level COMPANIES_DIR (L570) so the test suite can monkey-target a tmp
 tree without touching the constant.

 Body changes (additive blocks; existing logic preserved):

 1. Resolve companies_dir:
 companies_dir = companies_dir or COMPANIES_DIR
 1. Place this near the existing learnings_dir = base_dir or LEARNINGS_DIR at L1247.
 2. After existing result["ticker_lessons"] = filtered[:8] (L1315) and after result["global_lessons"] = sector_entries
  + macro_entries + cross_entries (L1404), but BEFORE the observability log.info(...) block (L1414), call a new helper
  to decorate each lesson and assemble the allowlist:
 _decorate_with_learner_paths(
     result, ticker=ticker,
     current_quarter_label=current_quarter_label,
     companies_dir=companies_dir,
 )
 3. Two module-scope helpers (defined just above build_learning_context). Two-phase design (per C5): phase 1 attaches
 paths only; phase 2 collects the allowlist in render order; phase 3 calls the invariant. Invariant is split out
 into its own function (per Fix 1) so tests can exercise the raise path directly with hand-crafted broken `lc`.

 def _assert_learner_paths_invariant(
     lc: dict,
     *,
     ticker: str | None = None,
     current_quarter_label: str | None = None,
 ) -> None:
     """Three-clause invariant on lc (per C1 strengthening, simplified per Fix #2):

       (A) Cross-surface set equality:
           set(lc["_allowed_learner_paths"]) == {every learner_result_path
           attached to any lesson in ticker_lessons or global_lessons}.
       (B) No duplicates in the allowlist list:
           len(allowlist) == len(set(allowlist)).
       (C) When ticker AND current_quarter_label are both provided (production
           path): the would-be self-path
             "earnings-analysis/Companies/{TICKER}/events/{Q}/learning/result.md"
           is NOT present in _allowed_learner_paths.

     Together A and C prove no self-path can leak: A guarantees both surfaces
     hold the same set; C guarantees that set excludes the current quarter.
     (Earlier draft had C also iterate lessons looking for self-path — that
     branch is unreachable without violating A first, so dropped per Fix #2 as
     defensive dead code.)

     Separately callable so tests can verify each clause independently. Uses
     explicit `raise AssertionError` (Q4) so `python -O` cannot strip the check.
     The decorator calls this AFTER allowlist assembly, with full context.
     """
     allowed = lc.get("_allowed_learner_paths") or []
     allowed_set = set(allowed)
     decorated: set[str] = set()
     for L in lc.get("ticker_lessons", []) or []:
         if "learner_result_path" in L:
             decorated.add(L["learner_result_path"])
     for L in lc.get("global_lessons", []) or []:
         if "learner_result_path" in L:
             decorated.add(L["learner_result_path"])

     # (A) cross-surface set equality
     if allowed_set != decorated:
         raise AssertionError(
             "learner_paths invariant (A) violated: allowlist set != decorated set "
             f"(allowlist={sorted(allowed_set)}, decorated={sorted(decorated)})"
         )

     # (B) no duplicates in list form
     if len(allowed) != len(allowed_set):
         raise AssertionError(
             f"learner_paths invariant (B) violated: duplicate paths in allowlist "
             f"(list={allowed})"
         )

     # (C) no self-path leak when context is known
     if ticker is not None and current_quarter_label is not None:
         self_path = (
             f"earnings-analysis/Companies/{ticker.upper()}/events/"
             f"{current_quarter_label}/learning/result.md"
         )
         if self_path in allowed_set:
             raise AssertionError(
                 f"learner_paths invariant (C) violated: self-path leaked into "
                 f"_allowed_learner_paths (self_path={self_path!r})"
             )


 def _decorate_with_learner_paths(
     lc: dict, *, ticker: str,
     current_quarter_label: str | None,
     companies_dir: Path,
 ) -> None:
     """Attach `learner_result_path` per-lesson + assemble `_allowed_learner_paths`.

     Mutates `lc` in-place. Two-phase per C5 (user requirement: collect AFTER
     decoration, not during).

       Phase 1 — attach paths only.
       PIT guard: skip emission whenever
         (source_ticker, quarter_label) == (ticker, current_quarter_label).
       Missing file: stat via `is_file()` (per C5 — stricter than `exists()`);
       omit the key entirely on miss.

       Phase 2 — collect _allowed_learner_paths in render order.
       Walk ticker_lessons (recency-desc), then global_lessons in render order
       (sector → macro → cross_ticker). First-seen dedupe.

       Phase 3 — invariant check via _assert_learner_paths_invariant with full
       context so all three clauses (A, B, C) fire.
     """
     # ── Phase 1: attach paths only ─────────────────────────────────────
     def _maybe_attach(entry: dict, src_ticker: str) -> None:
         # Flag 2 idempotency belt-and-suspenders: clear any stale value before
         # re-deciding. Defensive only — current flow calls the helper once per
         # bundle build, but a future re-run of this helper on an in-memory `lc`
         # whose underlying file disappeared between calls would otherwise leak
         # the stale path past the existence check.
         entry.pop("learner_result_path", None)
         ql = entry.get("quarter_label")
         if not ql or not src_ticker:
             return
         if current_quarter_label is not None \
            and src_ticker.upper() == ticker.upper() \
            and ql == current_quarter_label:
             return  # PIT guard — skip current-quarter self
         rel = (Path("earnings-analysis/Companies") / src_ticker.upper()
                / "events" / ql / "learning" / "result.md")
         abs_path = companies_dir / src_ticker.upper() / "events" / ql / "learning" / "result.md"
         if not abs_path.is_file():  # C5: is_file() not exists()
             return  # omit key
         entry["learner_result_path"] = str(rel)

     for lesson in lc.get("ticker_lessons", []):
         _maybe_attach(lesson, ticker)  # ticker_lessons: implicit source=current ticker
     for entry in lc.get("global_lessons", []):
         _maybe_attach(entry, entry.get("source_ticker") or "")

     # ── Phase 2: collect allowlist in render order, deduplicate ────────
     allowed: list[str] = []
     seen: set[str] = set()
     for lesson in lc.get("ticker_lessons", []):
         p = lesson.get("learner_result_path")
         if p and p not in seen:
             seen.add(p)
             allowed.append(p)
     for entry in lc.get("global_lessons", []):
         p = entry.get("learner_result_path")
         if p and p not in seen:
             seen.add(p)
             allowed.append(p)
     lc["_allowed_learner_paths"] = allowed

     # ── Phase 3: invariant check (full three-clause check, with context) ─
     _assert_learner_paths_invariant(
         lc, ticker=ticker, current_quarter_label=current_quarter_label,
     )

 3. Path construction note: Path("earnings-analysis/...") produces a repo-relative path with forward slashes on Linux
 (the deployment platform per CLAUDE.md). str(rel) yields exactly
 earnings-analysis/Companies/{TICKER}/events/{Q}/learning/result.md. The absolute stat check uses companies_dir / ...
 — separately constructed so the test suite can pass a tmp tree as companies_dir while the relative-path string
 remains the canonical, stable repo-relative form.
 4. The companies_dir / relative string MUST agree on the ticker case (.upper()) and quarter folder name
 (quarter_label verbatim). quarter_label matches the on-disk folder by construction (orchestrator L585 already uses
 quarter_info["quarter_label"] as the folder name).

 5.2 scripts/earnings/earnings_orchestrator.py::build_prediction_bundle (L238–246)

 This change has THREE parts (per C2 — the existing broad `except Exception` catches AssertionError, which would
 silently turn an invariant violation into a logged warning + empty learning_context, defeating the "loud
 invariant" claim):

 Current (L238–246, full block):
 try:
     sector = (results.get("8k_packet") or {}).get("sector") or _lookup_company_sector(ticker)
     bundle["learning_context"] = build_learning_context(
         ticker, sector=sector, pit_cutoff=pit_cutoff,
     )
 except Exception as e:
     log.warning("learning_context builder failed (non-fatal): %s", e)
     bundle["learning_context"] = {"ticker_lessons": [], "global_lessons": [],
                                    "ticker_ref": None, "global_ref": None}

 New:
 try:
     sector = (results.get("8k_packet") or {}).get("sector") or _lookup_company_sector(ticker)
     bundle["learning_context"] = build_learning_context(
         ticker, sector=sector, pit_cutoff=pit_cutoff,
         current_quarter_label=quarter_info.get("quarter_label"),
     )
 except AssertionError:
     # Pipeline invariant violation — re-raise so it surfaces visibly. NEVER
     # swallow into the broad-except fallback below; the invariant exists
     # specifically to halt production on inconsistent learner_paths state.
     raise
 except Exception as e:
     log.warning("learning_context builder failed (non-fatal): %s", e)
     bundle["learning_context"] = {
         "ticker_lessons": [], "global_lessons": [],
         "ticker_ref": None, "global_ref": None,
         "_allowed_learner_paths": [],   # C2: schema consistency on fallback
     }

 Three changes in this block (all required):
 1. Pass current_quarter_label so production hits the full PIT-guard + invariant clause-(C) path. quarter_info is
 in scope (function arg). The fail-closed validate_quarter_info at L194 guarantees quarter_label is non-None
 before this line runs (L77–82 raises if missing) — production never sees the safety-hatch default.
 2. `except AssertionError: raise` placed BEFORE the broad except. Without this, AssertionError is a subclass of
 Exception and the existing fallback at L243–246 would swallow invariant violations into a logged warning,
 exactly the silent-failure mode the invariant is meant to prevent.
 3. Add `_allowed_learner_paths: []` to the fallback dict for schema consistency. The renderer's
 `learning_ctx.get("_allowed_learner_paths") or []` already handles absence safely, but explicit emission keeps
 the fallback dict's shape parallel to the success path's.

 Diagnostic callers (compare_section.py, render_section.py) keep the safety-hatch default None; they remain
 functional and PIT clause-(C) is simply not enforced for them. (Follow-up PR can flip them to pass
 current_quarter_label explicitly. Out of scope here.)

 5.3 scripts/earnings/renderer/lessons.py::_render_learning_context

 Signature unchanged: def _render_learning_context(learning_ctx: dict) -> tuple[str, list[str]].

 Body changes (4 additive emissions; tuple element 2 unchanged):

 1. Allowlist block — after parts.append("## Prior Lessons (from learner)") (current L29) and BEFORE the empty-context
  check at L34:

 allowed = learning_ctx.get("_allowed_learner_paths") or []
 if allowed:
     parts.append("\n### Allowed learner reports for this prediction\n")
     for p in allowed:
         parts.append(f"- {p}")
     parts.append("")  # blank separator

 1. The allowlist block is rendered BEFORE the empty-context check so that an unusual state (lessons all PIT-filtered
 but allowlist somehow non-empty) still surfaces; in practice if both ticker_lessons and global_lessons are empty the
 allowlist will also be empty (by construction in §5.1) and the block is skipped. Order is preserved exactly as
 _allowed_learner_paths appears in the JSON (Q2 = render-order).
 2. Per-ticker-quarter learner_result: line — inside the for lesson in ticker_lessons: loop (current L41–58), after
 the why line (L57) and BEFORE the trailing parts.append("") (L58):

 path = lesson.get("learner_result_path")
 if path:
     parts.append(f"  - learner_result: {path}")

 2. One line per ticker-quarter block, last sub-bullet before the blank separator. Per D7: path is per-source-event,
 not per-text-bullet — even if a ticker-quarter has 4 predictor_lessons, only ONE learner_result: line is emitted for
 the whole quarter block.
 3. Per-global-lesson learner_result: continuation line — inside each scope's for entry in by_scope[…]: loop (current
 L71–96), after the parts.append(f"- [scope:…] (…) {lesson_text}") line, conditional on key presence:

 gpath = entry.get("learner_result_path")
 if gpath:
     parts.append(f"  learner_result: {gpath}")

 3. Three places to insert (sector, macro, cross_ticker). Two-space indent (continuation of the bullet, not a new
 bullet); contrast with ticker_lessons which uses   - learner_result: (sub-bullet) because ticker-quarter blocks have
 nested bullets already. Visually distinct: scope bullets have a one-line continuation; ticker-quarter blocks have a
 final sub-bullet.
 4. Tuple element 2 (ordered): NO change. Paths are rendering-only; do NOT append to ordered. Validator's positional
 lesson_labels contract preserved byte-identically. This is the single most important non-regression:
 test_R1_empty_context_returns_empty_list, test_R2_*, test_R3_*, test_R4_* must continue to pass UNCHANGED.

 Visual layout (Q5) when allowlist + ticker + globals are all populated:

 ## Prior Lessons (from learner)

 ### Allowed learner reports for this prediction
 - earnings-analysis/Companies/AVGO/events/Q3_FY2023/learning/result.md
 - earnings-analysis/Companies/CRM/events/Q1_FY2024/learning/result.md

 ### Ticker Lessons (1 most recent quarters)

 **Q3_FY2023** — prediction correct (short), actual -5.38%, driver: ex_ai_segment_deterioration
   - Predictor: …
   - Predictor: …
   - Data: …
   - Why: …
   - learner_result: earnings-analysis/Companies/AVGO/events/Q3_FY2023/learning/result.md

 ### Sector Lessons (1 entries)

 - [sector:Technology] (AVGO) In the 2023+ hyperscaler-AI-capex regime …
   learner_result: earnings-analysis/Companies/AVGO/events/Q3_FY2023/learning/result.md

 ### Macro Lessons (1 entries)

 - [macro] (AVGO) When a single-stock drawdown of ≥5% …
   learner_result: earnings-analysis/Companies/AVGO/events/Q3_FY2023/learning/result.md

 ### Cross-Ticker Lessons (1 entries)

 - [cross:AVGO,QCOM,AMD,TXN] (AVGO) These four large-cap semis …
   learner_result: earnings-analysis/Companies/AVGO/events/Q3_FY2023/learning/result.md

 5.4 .claude/skills/earnings-prediction/SKILL.md (D8(i))

 Operation: pure insert — three paragraphs between current L23 and L25 (the line ## Rules). No existing line is
 modified, deleted, reordered, or rewritten.

 Exact text to insert (starts with a leading blank line so the new paragraphs separate visually from L23, ends with a
 trailing blank line so the existing ## Rules heading at original L25 is still preceded by exactly one blank line):


 The rendered bundle's lessons section may carry an inline `learner_result: <path>` line under individual
 prior-quarter lessons, pointing to the previous learner's full `result.md` for that event. You MAY Read these files
 when the lesson body alone isn't enough to decide a label or ground a driver — for the prior learner's primary-driver
  call, what worked / what failed, and full evidence ledger. This is OPTIONAL; do not follow links by default.

 You may ONLY Read learner_result: paths that are explicitly listed under the "Allowed learner reports for this
 prediction" block in the rendered bundle (equivalently `learning_context._allowed_learner_paths` in the JSON — same
 set, two surfaces). Do NOT construct, guess, or pattern-extend additional paths from the format. The allowlist is the
  canonical PIT-safe set the orchestrator emitted for this prediction; any path not on it must not be Read, even if
 the directory layout would suggest one exists.

 When you cite material sourced from a learner result, set the `source` field in your `evidence_ledger` to
 `"learner_file:<path>"` (using the same path string from the allowlist) so the lineage is traceable in your output.


 (The fenced block above shows the literal characters to insert; the leading and trailing blank lines are part of the
 insert.)

 Verbatim-sentence audit: paragraph 2 contains, exactly word-for-word, "Do NOT construct, guess, or pattern-extend
 additional paths from the format." — the user's required verbatim core sentence. ✅

 ---
 6. Tests (TDD — failing first)

 6.1 New file: scripts/earnings/test_build_learning_context_paths.py

 16 cases (11 path-attach/allowlist + 4 invariant-function + 1 orchestrator call-site). Pure unittest (per C3 —
 matches existing test_learning_context.py style; no pytest fixtures). Path-attach tests use
 tempfile.TemporaryDirectory() set up in setUp() / cleaned in tearDown() for isolation from real
 earnings-analysis/. The 4 invariant tests do NOT need a tmp tree — they call orch._assert_learner_paths_invariant(...)
 directly with hand-crafted lc dicts.

 Module-level import (per C3): `import earnings_orchestrator as orch` — then access via orch.build_learning_context(...),
 orch._decorate_with_learner_paths(...), orch._assert_learner_paths_invariant(...). Reason: in TDD step 2 the
 helpers don't exist yet; using `from earnings_orchestrator import _assert_learner_paths_invariant` would error at
 import-time / collection-time. The dotted-attribute form fails per-test (clean red) instead of swallowing the file.

 Helper (test-internal): _make_learning_md(tmp_companies_dir, ticker, quarter) — creates
 {tmp_companies_dir}/{TICKER}/events/{Q}/learning/result.md with placeholder content.

 Helper (test-internal): _write_ticker_json(tmp_learnings_dir, ticker, lessons) — writes
 {tmp_learnings_dir}/ticker/{TICKER}.json with {schema_version: "ticker_lessons.v1", ticker, lessons: [...]}.

 Helper (test-internal): _write_global_json(tmp_learnings_dir, entries) — writes {tmp_learnings_dir}/global.json
 with {schema_version: "global_lessons.v1", entries: [...]}.

 setUp / tearDown skeleton (single fixture; reused across path-attach tests):
   class BuildLearningContextPathsTests(unittest.TestCase):
       def setUp(self):
           self._tmp = tempfile.TemporaryDirectory()
           self.tmp = Path(self._tmp.name)
           self.companies_dir = self.tmp / "Companies"
           self.companies_dir.mkdir()
           self.learnings_dir = self.tmp / "learnings"
           self.learnings_dir.mkdir()
       def tearDown(self):
           self._tmp.cleanup()

 Cases:

 #: 1
 Test name: test_ticker_lesson_path_attached_when_md_exists
 Setup: tmp ticker.json with one lesson Q1_FY2023; create Companies/AAPL/events/Q1_FY2023/learning/result.md
 Assertion: result["ticker_lessons"][0]["learner_result_path"] ==
   "earnings-analysis/Companies/AAPL/events/Q1_FY2023/learning/result.md"
 ────────────────────────────────────────
 #: 2
 Test name: test_ticker_lesson_path_omitted_when_md_missing
 Setup: tmp ticker.json with one lesson Q1_FY2023; do NOT create result.md
 Assertion: "learner_result_path" not in result["ticker_lessons"][0]
 ────────────────────────────────────────
 #: 3
 Test name: test_pit_guard_omits_current_quarter_for_ticker
 Setup: result.md exists for Q4_FY2023; current_quarter_label="Q4_FY2023"
 Assertion: "learner_result_path" not in result["ticker_lessons"][0]
 ────────────────────────────────────────
 #: 4
 Test name: test_global_lesson_path_uses_source_ticker
 Setup: global.json with source_ticker="MSFT", quarter_label="Q2_FY2024"; create
   Companies/MSFT/events/Q2_FY2024/learning/result.md
 Assertion: path equals earnings-analysis/Companies/MSFT/events/Q2_FY2024/learning/result.md
 ────────────────────────────────────────
 #: 5
 Test name: test_global_lesson_pit_guard_skips_when_source_ticker_quarter_match_current
 Setup: global with source_ticker="AAPL", quarter_label="Q4_FY2023"; current_ticker="AAPL",
   current_quarter_label="Q4_FY2023"; result.md exists
 Assertion: key absent on that entry
 ────────────────────────────────────────
 #: 6
 Test name: test_path_is_repo_relative_string
 Setup: any attached path
 Assertion: not p.startswith("/") and p.startswith("earnings-analysis/")
 ────────────────────────────────────────
 #: 7
 Test name: test_builder_default_when_current_quarter_label_is_none_attaches_all_existing_paths (renamed per Q4-extra)
 Setup: result.md exists for current ticker's lesson Q1_FY2023; current_quarter_label=None
 Assertion: path IS attached (PIT guard bypassed in safety-hatch mode)
 ────────────────────────────────────────
 #: 8
 Test name: test_allowed_learner_paths_in_exact_render_order (per Q2 + Fix #3)
 Setup: Build deterministic data: 2 ticker_lessons (T_recent attributed_at="2024-12-01", T_older
   attributed_at="2024-09-01"; both with result.md on disk under bundle's ticker AAPL); 1 sector lesson
   (source="MSFT", Q="Q1_FY2024"); 1 macro lesson (source="GOOG", Q="Q2_FY2024"); 1 cross_ticker lesson
   (source="META", Q="Q3_FY2024"); all five files exist
 Assertion: assertEqual(result["_allowed_learner_paths"], [t_recent_path, t_older_path, msft_sector_path,
   goog_macro_path, meta_cross_path]) — exact list equality, NOT membership. Verifies render-order:
   ticker_lessons by recency-desc → sector → macro → cross_ticker
 ────────────────────────────────────────
 #: 9
 Test name: test_allowed_learner_paths_excludes_current_quarter_self
 Setup: current quarter file exists but PIT-guarded; current ticker context provided
 Assertion: allowlist must NOT contain the current-quarter self path
 ────────────────────────────────────────
 #: 10
 Test name: test_allowed_learner_paths_dedupe_when_multiple_lessons_share_source
 Setup: global AND ticker lesson reference same (AAPL, Q1_FY2023); result.md exists
 Assertion: allowlist contains the path exactly once
 ────────────────────────────────────────
 #: 11
 Test name: test_allowed_learner_paths_empty_when_no_files_exist
 Setup: ticker + global lessons present in JSON but no result.md files on disk
 Assertion: result["_allowed_learner_paths"] == []
 ────────────────────────────────────────
 #: 12 (A)
 Test name: test_invariant_A_raises_on_cross_surface_drift
 Setup: Hand-craft lc = {"ticker_lessons": [{"learner_result_path": "earnings-analysis/X/A.md"}],
   "global_lessons": [], "_allowed_learner_paths": []} — decorated path exists but allowlist is empty.
   Call orch._assert_learner_paths_invariant(lc) (no context kwargs).
 Assertion: with self.assertRaises(AssertionError) as cm: orch._assert_learner_paths_invariant(lc) AND
   "invariant (A) violated" in str(cm.exception) AND sorted offending path appears in message
 ────────────────────────────────────────
 #: 12b
 Test name: test_invariant_passes_on_consistent_state_with_full_context
 Setup: Hand-craft consistent lc = {"ticker_lessons": [{"learner_result_path":
   "earnings-analysis/Companies/AAPL/events/Q1_FY2023/learning/result.md", "quarter_label": "Q1_FY2023"}],
   "global_lessons": [], "_allowed_learner_paths":
   ["earnings-analysis/Companies/AAPL/events/Q1_FY2023/learning/result.md"]}. Call with full context:
   orch._assert_learner_paths_invariant(lc, ticker="AAPL", current_quarter_label="Q4_FY2023") (Q1 ≠ Q4)
 Assertion: No exception raised. Covers A-positive, B-positive (no dupes), C-positive (no self-path) —
   guards against false-positive raises in any of the three clauses
 ────────────────────────────────────────
 #: 12c (B)
 Test name: test_invariant_B_raises_on_duplicate_in_allowlist
 Setup: Hand-craft lc = {"ticker_lessons": [{"learner_result_path": "X.md"}], "global_lessons": [],
   "_allowed_learner_paths": ["X.md", "X.md"]} (B-violation: duplicate). Call
   orch._assert_learner_paths_invariant(lc).
 Assertion: with self.assertRaises(AssertionError) as cm: ... AND "invariant (B) violated" in
   str(cm.exception) AND "X.md" appears twice in the listed allowlist message
 ────────────────────────────────────────
 #: 12d (C)
 Test name: test_invariant_C_raises_on_self_path_in_allowlist
 Setup: Hand-craft lc where _allowed_learner_paths contains
   "earnings-analysis/Companies/AAPL/events/Q4_FY2023/learning/result.md" AND a ticker_lesson carries the same
   path AND we call with ticker="AAPL", current_quarter_label="Q4_FY2023" (the self-path).
 Assertion: assertRaises(AssertionError) AND "invariant (C) violated" in str(cm.exception) AND
   "self-path leaked into _allowed_learner_paths" in message
 ────────────────────────────────────────
 #: 13
 Test name: test_orchestrator_call_site_passes_non_none_current_quarter_label
 Setup: Static-analysis-style: read scripts/earnings/earnings_orchestrator.py source, locate the
   build_learning_context( call inside build_prediction_bundle (near L240).
 Assertion: self.assertIn("current_quarter_label=quarter_info.get(\"quarter_label\")", source_text) —
   exact-match guard against future drops

 (Test count: §6.1 is now 16 cases — 11 path-attach + 4 invariant clauses (A-neg, full-positive, B-neg,
 C-neg-allowlist) + 1 orchestrator call-site. Total across all three test files becomes 16 + 6 + 1 =
 23 new cases. NOTE: the earlier draft contained a 12e test for "C-in-lesson-only" that was DROPPED per
 Fix #2 — the state it tries to construct is structurally unreachable without first violating clause A;
 the corresponding lesson-iteration branch in clause C was also removed as defensive dead code.)

 Test file imports (per C3 — module-level alias, NOT direct symbol import; private helpers may not exist
 yet during TDD red phase):
 import earnings_orchestrator as orch
 # usage in tests:  orch.build_learning_context(...), orch._decorate_with_learner_paths(...),
 #                  orch._assert_learner_paths_invariant(...)

 Sys.path setup: mirror existing test files (test_render_learning_context.py L21–23 —
 sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))).

 6.2 Extension: scripts/earnings/test_render_learning_context.py

 Append 6 cases to existing class (or add a sibling class RenderLearningContextPathsTests):

 #: R5
 Test name: test_R5_ticker_lesson_emits_learner_result_line_when_path_present
 Setup: dict with one ticker_lesson carrying learner_result_path; no global
 Assertion: " - learner_result: earnings-analysis/..." in text AND that line is the LAST sub-bullet of the quarter
   block (immediately before the trailing blank line)
 ────────────────────────────────────────
 #: R5b
 Test name: test_R5b_ticker_lesson_no_line_when_path_absent
 Setup: dict with ticker_lesson WITHOUT learner_result_path
 Assertion: "learner_result:" not in text
 ────────────────────────────────────────
 #: R6
 Test name: test_R6_global_lesson_emits_learner_result_line_when_path_present
 Setup: dict with one sector lesson carrying learner_result_path
 Assertion: " learner_result: earnings-analysis/..." in text (note: 2-space continuation, NOT  - learner_result:)
 ────────────────────────────────────────
 #: R7
 Test name: test_R7_ordered_tuple_unchanged_with_or_without_paths
 Setup: render same logical content twice — once with learner_result_path keys, once without
 Assertion: ordered list is byte-identical between the two renderings (validator contract preserved)
 ────────────────────────────────────────
 #: A1
 Test name: test_renderer_emits_allowlist_block_before_lesson_bodies
 Setup: dict with _allowed_learner_paths=[p1,p2] and at least one ticker_lesson
 Assertion: text contains "### Allowed learner reports for this prediction" and that heading appears at a string
 offset
   BEFORE the ### Ticker Lessons heading
 ────────────────────────────────────────
 #: A2
 Test name: test_renderer_omits_allowlist_block_when_list_empty
 Setup: dict with _allowed_learner_paths=[] and at least one ticker_lesson
 Assertion: "Allowed learner reports for this prediction" not in text

 6.3 New file: scripts/earnings/test_learner_paths_cross_surface.py

 1 case — guarantees the rendered allowlist block exactly mirrors the JSON _allowed_learner_paths.

 #: X1
 Test name: test_rendered_allowlist_block_set_equals_json_allowlist
 Setup: hand-craft a learning_context with mixed ticker + global decorated lessons + _allowed_learner_paths=[p1, p2,
   p3]; call _render_learning_context(lc) to get text; parse the rendered allowlist block by extracting all lines
 under
    ### Allowed learner reports for this prediction until the next ### heading or blank-line-then-heading boundary;
   strip leading -  to recover paths
 Assertion: set(parsed_paths) == set(lc["_allowed_learner_paths"]) AND len(parsed_paths) == len(set(parsed_paths)) (no

   dupes in render) AND order matches exactly (parsed_paths == lc["_allowed_learner_paths"])

 This is the cross-surface invariant the user explicitly required ("Renderer-block ↔ JSON-key equivalence guarantee —
 REQUIRED").

 6.4 Test execution command

 From repo root:
 venv/bin/python -m pytest scripts/earnings/test_build_learning_context_paths.py \
     scripts/earnings/test_render_learning_context.py \
     scripts/earnings/test_learner_paths_cross_surface.py \
     scripts/earnings/test_renderer_golden_full.py \
     scripts/earnings/test_renderer_golden_sections.py \
     scripts/earnings/test_learning_context.py \
     -v

 The last three are regression guards — they MUST continue to pass unchanged.

 ---
 7. Golden fixture handling

 Decision: zero golden regen. Existing fixtures are kept as-is.

 Why: existing golden_bundles/{T}_{Q}.json files do not contain the new keys (learner_result_path,
 _allowed_learner_paths). The renderer is implemented to be backward-compatible (dict.get("…") or [] for the
 allowlist; if path: guard for per-lesson lines). Therefore re-rendering existing golden bundles yields byte-identical
  output → existing goldens pass unchanged.

 If a golden test fails unexpectedly: that's a real regression in the renderer (e.g., emitting an empty allowlist
 block). Investigate root cause; do NOT regenerate goldens to mask it.

 If a future PR wants positive coverage in goldens (e.g., one fixture demonstrating the path emission end-to-end): add
  a NEW fixture pair (AVGO_Q4_FY2023_with_paths.json + matching *_with_paths.txt) and extend the EVENTS
 parameterization. Out of scope for THIS slice.

 ---
 8. Verification + smoke

 8.1 Test suite (must all be green)

 1. New tests: 16 builder + 6 renderer + 1 cross-surface = 23 NEW cases.
 2. Existing renderer tests (test_render_learning_context.py R1–R4): unchanged, still pass.
 3. Existing golden tests (test_renderer_golden_full.py, test_renderer_golden_sections.py): unchanged, still pass.
 4. Existing builder tests (test_learning_context.py, 24+ cases): unchanged, still pass — they ignore the new kwargs
 (default None matches their pre-existing behaviour).

 8.2 Live smoke — what each command verifies (per C6)

 Pre-req: an event whose prior quarter has a real result.md on disk. Per ls
 /home/faisal/EventMarketDB/earnings-analysis/Companies/AVGO/events/Q4_FY2023/learning/, AVGO Q4_FY2023 has result.md.

 The two smokes verify DIFFERENT properties — both are required:

 # Smoke 1 (lessons branch): emission + missing-file behaviour ONLY
 venv/bin/python scripts/earnings/render_section.py AVGO 0001730168-23-000044 lessons

 Path: render_section.py:55 calls build_learning_context(...) directly, WITHOUT current_quarter_label →
 safety-hatch mode → PIT clause-(C) is NOT enforced. Smoke 1 verifies: paths attach when result.md exists;
 allowlist populates; per-lesson learner_result: lines render; missing files produce no lines. Smoke 1 does
 NOT verify: orchestrator-level PIT propagation OR invariant clause (C). A bug there would not show up here.

 # Smoke 2 (full-bundle branch): full pipeline including PIT propagation
 venv/bin/python scripts/earnings/render_section.py AVGO 0001730168-23-000044 all

 Path: render_section.py:53 calls build_prediction_bundle(...) → which (after the §5.2 patch) passes
 current_quarter_label=quarter_info.get("quarter_label") → PIT clause-(C) IS enforced + invariant runs with
 full context. Smoke 2 verifies: orchestrator call-site propagation, invariant fires with ticker +
 current_quarter_label, current-quarter self-path is absent from allowlist.

 # Smoke 3 (real predict — most thorough): proves the production code path end-to-end
 venv/bin/python -m scripts.earnings.earnings_orchestrator \
     --ticker AVGO --quarter-info-json <path> --predict --pit <iso8601>

 This invokes the actual --predict flow that production uses. Most realistic but heaviest. Run at least once
 before declaring done.

 A bug in the orchestrator's current_quarter_label propagation would silently pass Smoke 1, fail Smoke 2/3.
 That's the whole point of C6's clarification.

 Pass criteria for smoke:
 - "### Allowed learner reports for this prediction" block appears immediately after ## Prior Lessons (from learner)
 heading, before ### Ticker Lessons.
 - Each path in the block is repo-relative and ends in learning/result.md.
 - For each ticker_lesson with a real result.md:   - learner_result: <path> appears as the last sub-bullet of its
 quarter block, before the blank separator.
 - For each global_lesson with a real result.md:   learner_result: <path> appears as a continuation under the bullet.
 - Set of paths in the allowlist block === set of paths in the inline learner_result: lines (manually eyeball).
 - No learner_result: lines for lessons whose result.md doesn't exist on disk.

 8.3 Bundle JSON verification

 After triggering an actual prediction (or running compare_section.py), inspect the saved
 events/{Q}/context_bundle.json:
 jq '.learning_context._allowed_learner_paths' events/{Q}/context_bundle.json
 jq '.learning_context.ticker_lessons[] | {ql: .quarter_label, p: .learner_result_path}'
 events/{Q}/context_bundle.json
 jq '.learning_context.global_lessons[] | {src: .source_ticker, ql: .quarter_label, p: .learner_result_path}'
 events/{Q}/context_bundle.json

 Confirm: every per-lesson learner_result_path (when present) appears in _allowed_learner_paths, and the count
 matches.

 8.4 SKILL.md verification

 grep -n "learner_result:" .claude/skills/earnings-prediction/SKILL.md
 grep -n "_allowed_learner_paths" .claude/skills/earnings-prediction/SKILL.md
 grep -n "Do NOT construct, guess, or pattern-extend" .claude/skills/earnings-prediction/SKILL.md
 grep -n "## Rules" .claude/skills/earnings-prediction/SKILL.md

 Confirm: 3 paragraphs inserted between L23 region and ## Rules. Verbatim core sentence present. Existing line numbers
  downstream of the insert have shifted by approximately +6 lines; existing tests / external refs to SKILL.md (none
 found in this scope) unaffected.

 ---
 9. Risks + edge cases

 #: R1
 Risk: Module-level COMPANIES_DIR constant (L570) used by other functions in orchestrator
 Mitigation: NOT changed. companies_dir kwarg defaults to COMPANIES_DIR. Other call sites unaffected
 ────────────────────────────────────────
 #: R2
 Risk: compare_section.py / render_section.py call build_learning_context without current_quarter_label → safety-hatch

   path → no PIT guard
 Mitigation: Documented per Q4-extra. Diagnostic-only callers; PIT-guard not load-bearing for non-production renders
 ────────────────────────────────────────
 #: R3
 Risk: Existing 24+ tests in test_learning_context.py call build_learning_context("AAPL", sector="Technology",
   base_dir=self.tmp) without the new kwargs
 Mitigation: Both new kwargs default to None; signature is purely additive. No test changes required. Verified by
   sample inspection of L291, L412, L478, L712 — all use kwargs sector + base_dir only
 ────────────────────────────────────────
 #: R4
 Risk: Path string platform mismatch (Windows vs Linux)
 Mitigation: Deployment is Linux-only (CLAUDE.md confirms). Path("earnings-analysis/...") produces forward-slash paths

   on Linux. str(Path) is stable
 ────────────────────────────────────────
 #: R5
 Risk: Self-check invariant fires in production due to a real bug
 Mitigation: Per §5.2's `except AssertionError: raise` (placed BEFORE the broad except), the AssertionError
   propagates up through build_prediction_bundle and ultimately fails the orchestrator run with a stack trace —
   the desired loud-failure behaviour. The fallback at L243–246 handles ONLY non-AssertionError builder failures
   (Neo4j hiccup, file permission). Production never produces silently-malformed bundles
 ────────────────────────────────────────
 #: R6
 Risk: Stat call cost
 Mitigation: At most 18 Path.is_file() calls per bundle (8 ticker + 4+4+2 global). Stricter than exists() per C5
   — rejects directories and dir-symlinks at the path. Negligible vs. concurrent builder work
 ────────────────────────────────────────
 #: R7
 Risk: Renderer drift breaking existing goldens
 Mitigation: Renderer changes are gated on key presence (if path:, if allowed:). Backward-compat is the design goal.
   Golden tests are the regression net — any unexpected drift fails them, signalling a bug
 ────────────────────────────────────────
 #: R8
 Risk: _decorate_with_learner_paths mutates the lesson dicts that are shared with learnings/ticker/{T}.json raw data
 Mitigation: The raw data was loaded via json.loads(...).get("lessons", []) (L1297) — that's a fresh deep-copy, not a
   reference into the file. Mutating is safe; no write-back
 ────────────────────────────────────────
 #: R9
 Risk: quarter_label from a malformed ticker.json entry
 Mitigation: Existing handler (L1304) defaults to ""; _maybe_attach early-returns when not ql. Defensive
 ────────────────────────────────────────
 #: R10
 Risk: source_ticker empty / null on a global entry
 Mitigation: Validator-enforced upstream (L1148: .upper().strip()); _maybe_attach early-returns when not src_ticker.
   Defensive
 ────────────────────────────────────────
 #: R11
 Risk: Stale-content risk on result.md (Flag 1). The plan PIT-guards the path EMISSION (current-quarter guard +
   source_pit_cutoff filter at build_learning_context L1272–1288), but it does NOT validate that the FILE'S CONTENT was
   authored before the predictor's PIT cutoff. If a learner re-ran a prior quarter with a later cutoff, the on-disk
   result.md content could embed post-cutoff information that the predictor would then read.
 Mitigation: This is a learner-discipline concern, not a defect in this slice. Boundary acknowledged: the
   path-emission contract is "the path points to the most recent successfully-written learner artifact for that
   (source_ticker, quarter_label) — its CONTENT is governed by whatever PIT discipline the learner enforced at write
   time." Long-term remedy (out of scope here): add a content-PIT stamp inside result.md that the predictor can
   verify, or attach a `result_md_pit_cutoff` sidecar field per lesson. Track as a follow-up.

 ---
 10. Execution order

 Strict TDD sequence. Each step has a clear pass/fail criterion. Stop at the first failure and investigate root cause
 before continuing.

 1. Read & confirm baseline: re-run pytest scripts/earnings/test_render_learning_context.py
 scripts/earnings/test_renderer_golden_full.py scripts/earnings/test_renderer_golden_sections.py
 scripts/earnings/test_learning_context.py -v. Confirm all green.
 2. Write test_build_learning_context_paths.py (16 cases). Run → expect 16 failures (functions not yet
 defined: cases #1–#11 fail with AttributeError on orch._decorate_with_learner_paths etc; #12, #12b, #12c, #12d
 fail with AttributeError on orch._assert_learner_paths_invariant; #13
  passes only after the orchestrator call-site update lands in step 6). Verify failure modes match expected — i.e.,
 not import errors at the file level.
 3. Write extension to test_render_learning_context.py (6 cases). Run → expect 6 failures.
 4. Write test_learner_paths_cross_surface.py (1 case). Run → expect 1 failure.
 5. Implement _decorate_with_learner_paths + signature change in build_learning_context (per §5.1).
 6. Update build_prediction_bundle call site (per §5.2).
 7. Run builder tests: pytest scripts/earnings/test_build_learning_context_paths.py -v. Expect 16 green.
 8. Run existing builder tests: pytest scripts/earnings/test_learning_context.py -v. Expect all green (regression
 check).
 9. Implement renderer changes (per §5.3).
 10. Run renderer tests: pytest scripts/earnings/test_render_learning_context.py
 scripts/earnings/test_learner_paths_cross_surface.py -v. Expect (4 R1-R4 unchanged + 6 new + 1 cross-surface) = 11
 green for these specific files.
 11. Run golden tests: pytest scripts/earnings/test_renderer_golden_full.py
 scripts/earnings/test_renderer_golden_sections.py -v. Expect all green (backward-compat check).
 12. Apply SKILL.md insert (per §5.4). Verify with the 4 grep commands in §8.4.
 13. Live smoke: run render_section.py AVGO 0001730168-23-000044 lessons and … all. Eyeball-check per §8.2 pass
 criteria.
 14. Done: report all-green with file diffs summarized.

 If any step fails, halt and investigate. Do not patch tests to mask implementation bugs; do not edit goldens to mask
 renderer drift.

 ---
 11. Glossary (for fast re-orientation later)

 - learner_result_path: per-lesson key in JSON pointing to repo-relative path of the prior learner's result.md.
 - _allowed_learner_paths: top-level allowlist in learning_context; the canonical PIT-safe set the predictor may Read.
 - PIT guard (here): (source_ticker, quarter_label) != (current_ticker, current_quarter_label).
 - Cross-surface equivalence: set(rendered allowlist block) == set(JSON _allowed_learner_paths) AND list ordering
 matches exactly.
 - Safety-hatch mode: current_quarter_label=None (diagnostic callers); PIT guard not enforced; file-existence check
 still applies.