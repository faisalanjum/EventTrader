# Earnings Refactor Safety Contract

Last updated: 2026-05-07, after quarter-resolver Goals 6c/6e and Goal 6f research setup.

This document exists because several recent fixes look removable or simplifiable in isolation, but are load-bearing. Read this before changing:

- `scripts/earnings/earnings_orchestrator.py`
- `scripts/earnings/builders/`
- `scripts/earnings/renderer/`
- `scripts/earnings/tests/`
- `.claude/skills/earnings-prediction/SKILL.md`
- `scripts/earnings/quarter_identity.py`
- `scripts/harvest_guidance_sessions.py`

For rearchitecture work, preserve behavior first. Make output byte-identical before attempting any semantic cleanup.

## Source Of Truth

1. `earningsBundleRenderer.md` is the authoritative audit/status plan.
2. This file is the preservation contract for refactors.
3. `earnings-bundle-audit-prompt.md` is the workflow prompt. If it conflicts with this file, follow this file.

## Refactor Goal

Acceptable:

- reduce duplication;
- extract coherent helpers;
- isolate orchestration concerns;
- make builder/renderer contracts clearer;
- improve test ergonomics without deleting coverage.

Not acceptable:

- line-count reduction by deleting explicit checks;
- changing rendered output during a "pure refactor";
- removing goldens or tests as "bloat";
- making JSON the predictor's primary surface;
- weakening PIT, source-id, or lesson-label contracts.

## Must-Preserve Invariants

### Cross-surface contract

1. Rendered text remains the predictor's primary reasoning surface.
2. JSON remains verification-only: exact precision, structural fields, builder errors, source catalogs.
3. Both paths remain available to the predictor. Neither should be dropped.
4. `context_bundle.json` schema is append-only for this audit surface. Do not rename or remove existing fields.

### U64 quarter identity / PIT masking

5. Production 8-K quarter identity is Candidate D in `scripts/earnings/quarter_identity.py` (Goal 6c, commit `a61636a`, pushed). It is a PIT-safe prior-periodic projection resolver, not pure fiscal math.
6. `resolve_quarter_info(ticker, accession_8k)` returns a dict with `quarter_label`, `safety_action`, `quarter_identity_source`, and diagnostics. Callers must trust `quarter_label` only when `safety_action == "AUTO_OK"`.
7. Cold-start is handled inside the resolver: if no PIT-visible prior 10-Q/10-K exists, return `FAIL_CLOSED` (source `prior_periodic_projection_no_prior` or equivalent), not a guessed label.
8. Candidate D measured rates: warm-start historical `9491/9878 = 96.08%` correct, `24/9878 = 0.24%` wrong, `363/9878 = 3.67%` fail-closed; latest-per-ticker live proxy `747/781 = 95.65%` correct, `3/781 = 0.38%` wrong, `31/781 = 3.97%` fail-closed.
9. Preserve Goal 4 Rule F behavior for odd 52/53-week cases: 115-row set must remain `94 OK / 0 WRONG / 21 FAIL_CLOSED`; FCX `0000831259-26-000021` must remain `Q1_FY2026 / AUTO_OK / prior_periodic_projection_q4_to_q1`.
10. Preserve the orchestrator destructive-write guard from Goal 4: earnings event bundles/predictions/learner artifacts must not be written/destructively overwritten unless quarter resolver returns `AUTO_OK`.
11. Do not resurrect `_STALE_MATCH_DAYS=150`; it caused the FCX Q1 FY2026 -> Q4 FY2025 bug.
12. Do not add ticker tables, issuer FY-convention tables, sector/industry/SIC/GICS/NAICS dispatch, EX-99.1 parsing, external APIs, ML/LLM classifiers, or arbitrary new thresholds to the resolver.
13. Preserve SEC `period_of_report` byte identity for historical fixtures.

**Why rule 12 bans XBRL-FY-trust tables and EX-99.1 parsing**: iXBRL `DocumentFiscalYearFocus` for an FYE-January issuer is filed under year-of-start convention (a 10-K covering Feb 2024 – Jan 2025 reports `FY=2024`); the same issuer's EX-99.1 press release calls the same period `FY 2025` (year-of-end). Both labels are "correct" for their audience; they disagree on the wire. Any production rule that trusts XBRL `FY` on FY-disagreement (proposed Rule G2) systematically wrong-writes the year for ~10% of off-calendar issuers. The deeper mechanism (per `GOAL6F_FAILURE_MODEL.md`) is "structural ambiguity after FY disagreement" — the same prior structural shape produces both safe and unsafe rows; no allowed signal uniquely discriminates. Empirically validated 2026-05-07 against 408 rows × 34 edge tickers: `DECISION_FLAG_RULE_G2 = promising_but_not_shippable` (+37–39 new wrong AUTO_OK on Tier A+B; failure clusters GIII/BOX/WDAY/WMS/NTAP/NTNX/DKS/ANF). Goal 6f then tested 4 additional structural candidates beyond G2; all rejected: `MULTI_PRIOR_STABLE_OFFSET` (+17 new wrongs), `PERIOD_END_SHAPE_GATE` (+39 new wrongs), `CURRENT_8K_OWN_XBRL` (no-op — feature pipeline lacks current-8K DEI facts), `ADVANCE_RESULT_AGREEMENT` (no-op — zero edge convergences). `DECISION_FLAG_GOAL6F_RECOMMENDATION = KEEP_D`. Rule F `rule_f_fail_closed_fy_disagreement` (Goal 4) and the calendar-branch `rule_g_fail_closed_*_calendar` guards (Goal 6c) intentionally fail-closed on this class. Approximately 4.4% of the universe (34/781 latest-per-ticker proxy) is structurally fail-closed under current locks and is expected to remain so. Do not "fix" the FY-disagreement guard without re-running the 34-ticker audit AND the Goal 6f matrix and beating both. Future research lead (data-layer, not resolver-rule): if the feature pipeline ever exposes 8-K cover-page DEI FY/Q facts, retest `CURRENT_8K_OWN_XBRL`.

### Guidance quarter-label boundary

14. Guidance has two separate fiscal-identity concepts: source-quarter labeling for guidance thinking harvest/event folders, and guidance target periods extracted by the guidance writer. Do not merge them.
15. `scripts/harvest_guidance_sessions.py` 8-K source-quarter path uses `resolve_quarter_info()`, so future 8-K resolver improvements are picked up there automatically.
16. `scripts/harvest_guidance_sessions.py` 10-Q/10-K fallback is intentionally separate: it labels the periodic filing itself. Goal 6e (commit `be4c2cc`) hardened only the rare case where `Report.fiscal_quarter/fiscal_year` are NULL: compute math fallback, optionally override with the filing's own XBRL DEI FY/Q only when not denylisted and plausible via `should_use_xbrl_fiscal`; triple-check denylist against `accession`, `report_id`, and `accession_no`.
17. Future changes to low-level helpers (`parse_xbrl_fiscal_identity`, `should_use_xbrl_fiscal`, `XBRL_DENY_PERIODIC_ACCESSIONS`) can benefit both quarter resolver and guidance periodic fallback. Future changes to `resolve_quarter_info()` itself do not automatically affect the 10-Q/10-K fallback.
18. Do not swap `resolve_quarter_info()` into the 10-Q/10-K fallback. A 10-Q/10-K should use its own stored fiscal label, then own XBRL label, then math fallback.

### U65 bundle path scoping

19. `--save-dir` must remain run-scoped. Do not restore `Path(save_dir).parent` behavior.
20. Parallel prediction runs must not share `/tmp/context_bundle.json` or `/tmp/context_bundle_rendered.txt`.

### U67 evidence grounding

21. `evidence_source_catalog` IDs are event-scoped. The event prefix is load-bearing:
    `SRC:<ticker>:<quarter_label>:<accession_8k>#<location>`.
22. `validate_prediction_result(..., expected_source_ids=...)` must enforce set membership in production.
23. Empty `evidence_ledger` is rejected in production validation.
24. The production orchestrator call should fail loudly if the bundle catalog is missing. Do not silently fall back to `None`.
25. External A/B or calibration harnesses that pass `expected_source_ids=None` are intentionally legacy/offline. Do not "dedupe" those into strict production behavior without migrating the harnesses.
26. Keep rendered `N{i}` and `F{i}` aliases in the catalog; the predictor sees those in rendered text.
27. Keep raw `event_ref` anchors too; they provide traceability.
28. Macro catalyst shapes differ by bucket:
    - `today` / `yesterday`: `{date, headlines: [headline_dict, ...]}`
    - `earlier`: `[[date_str, headline_dict], ...]`
    Do not normalize this away in the catalog walk unless tests prove every existing fixture still has anchors.
29. `prediction_validated` must gate result quarantine. A bare exception handler can quarantine a valid `result.json` after validation succeeds but ledger closing fails.

### U45/U66 lessons contract

30. `iter_labeled_lessons()` in `_text_utils.py` is the shared source of truth for:
    - renderer L# ordering;
    - U67 catalog `#S10.lesson.L#` anchors.
    Do not inline or duplicate it.
31. `_render_learning_context()` returns `(text, ordered_lesson_texts)`. The second tuple element is validator-critical and must preserve the exact ordered lesson bodies.
32. `## Lessons To Label` contains labelable lesson bodies only. Scope tags belong on the marker line, not inside `lesson_text`.
33. `## Context-Only` content is background only. It must not become `lesson_labels[]`.
34. Empty learning context still renders the outer `## Prior Lessons (from learner)` section and `No prior lessons available...` message. Do not add an outer guard in `renderer/bundle.py` that skips lessons entirely.
35. Empty `related_tickers=[]` renders a bare `L#.` marker, not `[cross:]`.
36. Flat L1..Ln numbering across ticker -> sector -> macro -> cross_ticker is intentional.
37. Do not dedupe duplicate lesson bodies across scopes. Positional labels are intentional.
38. SKILL.md Phase 0 source of truth is rendered `## Lessons To Label`, not `bundle.learning_context` JSON.
39. The `learner_result:` allowlist is PIT-safe. Do not invent paths from directory shape.

### Tests and golden fixtures

40. Golden render fixtures are not bloat. They catch behavior drift.
41. Degraded goldens are not optional. They caught the U45 empty-case followup fixed in `624317c`.
42. Targeted tests and full/section/degraded goldens serve different purposes; do not collapse them into one weak smoke.
43. A pure refactor should not change golden output.

## Common Bad Refactors

Avoid these even if they appear simpler:

- Inline `iter_labeled_lessons` into `renderer/lessons.py` and the catalog builder separately.
- Replace raw/display periodic accession split with one field.
- Add an outer `if learning_context` guard around `_render_learning_context`.
- Remove `prediction_validated` as "unnecessary state."
- Replace explicit legacy `expected_source_ids=None` callsites with default production validation.
- Sort source catalogs alphabetically; render order matters for predictor lookup.
- Remove rendered source-id catalog because JSON already has it.
- Remove degraded goldens because they are "just fixtures."
- Change SKILL.md during a pure Python refactor.
- Treat `earnings-bundle-audit-prompt.md` historical sections as newer than `earningsBundleRenderer.md`.
- Put Candidate D into `fiscal_math.py`. Candidate D needs PIT filing metadata and prior periodic/XBRL context; `fiscal_math.py` stays pure date math.
- Add ticker/industry/FY-convention maps to close Candidate D fail-closures. Use research-only Goal 6f if exploring structural alternatives.
- Use EX-99.1/press-release text as production quarter identity. It is allowed only as research ground truth/evidence, not runtime logic.
- Swap `resolve_quarter_info()` into 10-Q/10-K guidance fallback. Periodic filings should use their own stored/XBRL labels, not the earnings 8-K resolver.

## Required Gates

Before editing:

```bash
git rev-parse HEAD
venv/bin/python -m pytest scripts/earnings -q
venv/bin/python -m scripts.earnings.tests._capture_golden full
venv/bin/python -m scripts.earnings.tests._capture_golden sections
venv/bin/python -m scripts.earnings.tests._capture_golden degraded
git status --short
```

After every behavior-preserving commit:

```bash
venv/bin/python -m pytest scripts/earnings -q
venv/bin/python -m scripts.earnings.tests._capture_golden full
venv/bin/python -m scripts.earnings.tests._capture_golden sections
venv/bin/python -m scripts.earnings.tests._capture_golden degraded
git diff -- scripts/earnings/tests/fixtures/golden_renders scripts/earnings/tests/fixtures/golden_bundles
```

Expected for pure refactor:

- tests pass;
- no golden diff;
- no SKILL.md diff;
- no bundle schema field rename/removal.

If any golden diff appears, stop and classify it:

- expected output change for an approved U-item, or
- accidental regression.

Do not continue through an unexplained golden diff.

If your diff touches `scripts/earnings/quarter_identity.py` or `scripts/earnings/earnings_orchestrator.py`, also run the immutable Goal verifier:

```bash
venv/bin/python earnings-analysis/canary/quarter_resolver/verify_goal4_implementation.py
```

Hard-locks: G5 = `94 OK / 0 WRONG / 21 FAIL_CLOSED` on the 115 odd_52_53 set; G6 = FCX `0000831259-26-000021` returns `Q1_FY2026 / AUTO_OK / prior_periodic_projection_q4_to_q1`; G7 = `9116 OK / 0 WRONG / 827 FAIL_CLOSED` on 9,943 oracle rows; G7b = 9,860 currently-firing rows preserved; G8/G9 = pytest including write-guard. Verifier refuses to run if its own file has uncommitted changes (anti-tampering). The Goal 6c per-row D-baseline match against `goal6a_d_measurement.csv` is enforced inside `scripts/earnings/test_quarter_identity.py`.

## Suggested Refactor Sequencing

Do not start with a repo-wide rewrite. Prefer:

1. Finish U22+U22a if the user wants correctness before architecture.
2. Finish U33 if live pre-market matters.
3. Then behavior-preserving consolidation.

For consolidation:

1. Read-only module map.
2. Extract tiny helpers with no output change.
3. Split `earnings_orchestrator.py` by responsibility only after its invariants are mapped.
4. Refactor builders and renderers in separate sessions.
5. Keep `lessons.py`, `_text_utils.iter_labeled_lessons`, U67 catalog, and validator callsites especially conservative.

## Smoke Fixtures

Use these roles when smoke infrastructure is available:

- AVGO Q4 FY2023: rich lesson context, 6 L# markers.
- CRM Q3 FY2024: empty-lessons render path.
- AAPL Q4 FY2023: large U67 catalog, many source IDs.
- NVDA Q3 FY2024: peer/exhibit stress path.
- FCX Q1 FY2026 (accession `0000831259-26-000021`): U64 canary. Resolver must return `Q1_FY2026 / AUTO_OK / prior_periodic_projection_q4_to_q1`. Any other outcome means the resolver regressed. This is the load-bearing fix for the entire quarter-resolver workstream.

If a smoke cannot be run due to credentials, network, or local services, say that explicitly.

## What To Tell The User Before Editing

For any proposed refactor, state:

- which invariant it touches;
- why behavior should remain identical;
- which tests/goldens protect it;
- what files will change;
- what files will not change.

If the change touches U64, U67, U45/U66, or SKILL.md, ask for explicit approval before editing.

If the change touches `quarter_identity.py` or guidance source-quarter labeling, also state whether it changes:

- Goal 6c Candidate D behavior;
- Rule F odd 52/53 behavior;
- FCX Q1 FY2026 resolver outcome;
- the orchestrator `AUTO_OK` write guard;
- the 10-Q/10-K guidance fallback boundary.
