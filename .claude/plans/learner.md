# Earnings Learner — Final Design

**Created**: 2026-04-16
**Status**: APPROVED — all decisions locked, ready for implementation

### Human Review Gates (must be validated by user before calibration)

1. **SKILL.md prompt quality** — every single line of `.claude/skills/earnings-learner/SKILL.md` must be reviewed and approved. This is the learner's reasoning contract — no bot-only sign-off.
2. **PIT cutoff correctness** — verify that `get_quarterly_filings()` produces the correct next-quarter boundary across all tickers, including edge cases (annual quarters, deferred learners, first/last quarter).
3. **Lesson quality and evidence surface** — validate that the learner uses the full relevant evidence surface (all Data SubAgents, context bundle, post-event data) and converts findings into reusable, high-signal guidance rather than quarter-specific summaries.
**Parent plan**: `earnings-orchestrator.md` — this file supersedes the attribution/learner sections (§2d, §4) in the parent plan for all learner contract decisions

---

## Outstanding Follow-Ups / TODO

Canonical actionable backlog for the learner subsystem. Supersedes the backlog lists in `learner-edits.md` §10 and §12 (those sections now cross-reference here). Items grouped by priority; detailed designs and rejected-alternatives remain in `learner-edits.md`.

### 🔥 Blocker — T1.5: PIT correctness end-to-end (blocks T1, T2, T3, T4, and any historical re-run)

**Status as of 2026-04-17**: ✅ **code + tests shipped on `origin/main`** — T1.5a + T1.5b implementation in `1b79614` (bundled with the external-harvester commit; PIT work not mentioned in that commit message); tests + plan + datetime-aware filter fix in `fe0326a`. 86 targeted tests green (13 R18 + 14 R17 + 59 pre-existing). Discovered during post-§8.3-migration verification of the AVGO 3-quarter corpus. **Pending operational step**: corpus wipe + PIT-safe rerun (task #356) — required before T4 A/B measurement; optional for T1/T2/T3 development since T1.5b's legacy-entry filter soft-quarantines contaminated entries in historical mode.

#### Summary of the defect

The historical re-run pipeline has two independent PIT-leak bugs and one residual graph-state leak that together make every prediction + lesson produced under §8.3 hindsight-contaminated:

| # | Item | Severity | Summary | Where to start |
|---|---|---|---|---|
| T1.5a | **Bundle-PIT default** in `earnings_orchestrator.main()` | 🔴 Root cause — dominant | Orchestrator takes `args.pit` literally; when `--predict`/`--learn` is set without `--pit`, every builder silently falls into live mode and anchors to `_now_iso()`. Every bundle surface except `8k_packet` (accession-anchored) and `inter_quarter_context` (self-anchored to filing) reads data as of run-time wall-clock. | `scripts/earnings/earnings_orchestrator.py::main()` argparse / pre-dispatch block: default `args.pit = quarter_info['filed_8k']` when `--predict`/`--learn` is set and `--pit` is absent. Add `--live` opt-in to preserve intentional live-mode use. |
| T1.5b | **Lesson-PIT plumb-through + schema** in `build_learning_context()` | 🔴 Secondary | Function has no `pit_cutoff` parameter; read path is unfiltered across **all four** scopes (ticker, sector, macro, cross_ticker). Even with T1.5a fixed, chronologically-later lessons leak into earlier predictor contexts. Neither `source_filed_8k` nor `source_pit_cutoff` is stored on entries — no correct field exists to filter on. | `scripts/earnings/earnings_orchestrator.py:2174` signature + writers at `append_global_lessons` (line 2085) / `append_ticker_lesson` (line 2035). Schema extension to entry shape; visibility predicate `source_pit_cutoff <= pit_cutoff`. |
| T1.5c | **Residual graph-state leaks** in peer selection and sector lookup | 🟡 Acknowledge, defer | Even with T1.5a+b merged, `peer_earnings_snapshot` Cypher selects peers via current `BELONGS_TO` Industry edges and ranks by current `peer.mkt_cap`; `_lookup_company_sector` returns current sector; write-side `source_sector` stamp is today's sector. Practical impact is small for AVGO/NVDA/BURL (stable classifications); systemically real for cohort expansion. | Documented as **T20** in the 🟡 Backlog below. No immediate fix required. |

#### Evidence (empirical, verified from actual bundles in the current corpus)

All three AVGO quarters (Q1/Q2/Q3 FY2023, events filed Mar/Jun/Aug **2023**) share the same signature:

```
context_bundle.pit_cutoff              = null
peer_earnings_snapshot.source_mode     = "live"
peer_earnings_snapshot.effective_cutoff_ts = "2026-04-17T..." (today)
peer_earnings_snapshot.window_start    = "2026-03-03"       (today − 45d)
peer_earnings_snapshot.peer_tickers    = ["MU","MRVL","SMTC"]  (2026 rankings)
macro_snapshot.effective_cutoff_ts     = "2026-04-17T..." (today)
guidance_history.source_mode           = "live"
consensus.source_mode                  = "live"
prior_financials.source_mode           = "live"
```

Root-cause pointers:
- `/tmp/rerun_master.sh:128` invokes orchestrator **without** `--pit`.
- `earnings_orchestrator.main()` passes `args.pit=None` straight through to `run_core_flow(pit_cutoff=None)` → `build_prediction_bundle(pit_cutoff=None)` → every adapter cascades into live mode.
- Lesson read path at `earnings_orchestrator.py:2174` (signature) and the for-loop over `entries` (lines ~2243–2280) has no timestamp filter on any scope — not just cross_ticker/sector, but **also macro and ticker**.

Asymmetry observation: the LEARNER side correctly derived PIT via `derive_learner_pit()` at line 1711; stored attribution results have `pit_cutoff: "2023-06-01T..."` for Q1_FY2023. Learner honest, predictor dishonest → lessons are produced by honest reasoning over hindsight-assisted predictions → **doubly contaminated**.

#### Visibility predicate (decided, principled)

```
lesson visible at predictor.pit_cutoff iff lesson.source_pit_cutoff <= predictor.pit_cutoff
```

Chosen over the looser `source_filed_8k <= predictor.pit_cutoff` because it simulates production learner-write timing: a lesson cannot be produced in production until the next quarter's data arrives (the learner's own pit_cutoff). Ignoring SDK latency, this is the tightest honest bound. When `predictor.pit_cutoff is None` (live production), the filter is bypassed entirely — real-time behavior preserved exactly.

#### Schema note — where the new fields live and what validates them

`source_filed_8k` and `source_pit_cutoff` are **Python-stamped storage metadata on global.json / ticker/*.json entries**, *not* new fields in the learner's output contract. `attribution_result.v2` already carries `filed_8k` and `pit_cutoff` as top-level fields (required by SKILL.md §"Required top-level fields"); Python's `append_global_lessons` / `append_ticker_lesson` simply copy those values into each entry and rename them with the `source_` prefix (meaningful at entry scope — "the lesson's source event's filed_8k / pit_cutoff").

Implications:
- **No change to `validate_attribution.py`.** The learner-output contract is untouched; existing V-rules continue to enforce `filed_8k` / `pit_cutoff` at top level.
- **Validation of the new entry fields happens in `test_learning_context.py` (R17a below)** and at read-time in `build_learning_context`, which treats absent fields as legacy — counted and dropped in historical mode, passed through in live mode.
- If a dedicated storage-schema validator is later desirable (e.g., a `validate_global_entry.py` helper), it lives **outside** the learner contract layer. Out of scope for T1.5.

#### Tests shipped (`test_learning_context.py::PITFilterTests` + `test_orchestrator_pit_mode.py::ResolvePITMode`)

**14 R17 tests** — read-side lesson filter + writer-side schema stamping:

- `R17a` — writer stamps `source_filed_8k` + `source_pit_cutoff` on new global **and** ticker entries (two sub-tests).
- `R17b` — historical filter includes/excludes entries correctly across **all four** scopes (ticker, sector, macro, cross_ticker) (two sub-tests: straddle-exclusion and straddle-inclusion).
- `R17c` — live preservation: `pit_cutoff=None` bypasses filter; production behavior unchanged.
- `R17d` — macro-scope regression guard (the scope easiest to miss during implementation).
- `R17e` — observability: `ticker_post_cutoff` + `global_post_cutoff` appear in the always-fires log line even when zero.
- **`R17_legacy`** — legacy entries (no `source_pit_cutoff`) excluded in historical mode, passed through in live mode (two sub-tests).
- **`R17f` (post-external-review regression suite)** — datetime-aware comparison correctness: (i) mixed-offset source chronologically later → excluded; (ii) mixed-offset source chronologically earlier → included (both guard against naive string comparison); (iii) `Z` suffix parsed as UTC; (iv) malformed timestamp defensively excluded; (v) tz-naive timestamp defensively excluded.

**13 R18 tests** — `_resolve_pit_mode(args, quarter_info) -> (pit_cutoff, mode)`:

- `R18a` — historical default fires on `--predict`, `--learn`, or both (three sub-tests).
- `R18b` — `--live` opt-in produces `(None, "live")` with or without `--predict` (two sub-tests).
- `R18c` — explicit `--pit` ISO wins over default, with or without `--predict` (two sub-tests).
- `R18d` — `--live` and `--pit` are mutually exclusive → `ValueError` (two sub-tests; XOR guard per external review).
- **`R18e`** — no flags → inspection mode stays live (`--save` alone doesn't trigger historical default).
- **`R18f`** — missing `filed_8k` in quarter_info: raises on default path; OK under explicit `--live` or `--pit` (three sub-tests).

**Bonus**: `R18d`'s rerun-harness parity check (`/tmp/rerun_master.sh` unchanged, its invocations now produce PIT-safe bundles automatically) verified via the smoke script (`/tmp/smoke_t1_5.py`, not versioned).

#### Corpus implications

- **Current 3-AVGO quarter corpus is PIT-poisoned and must be wiped before T4.** `global.json` (9 entries) + `ticker/AVGO.json` (3 lessons) are artifacts of hindsight-assisted predictions; they cannot be salvaged through read-side filtering.
- Backup `earnings-analysis/learnings.backup.1776447824` is unaffected and remains the rollback source for the pre-migration legacy-schema corpus.
- Any future historical re-run (3 AVGO, 15-quarter, or expansion) **requires T1.5a + T1.5b merged first**. Without them, re-contamination is guaranteed.
- Behavior changes by caller type (T1.5a is the only one with production-visible effects; T1.5b is purely additive when `pit_cutoff=None`):
  - **Genuine real-time invocations** (a fresh 8-K firing now, `--predict`/`--learn` without `--pit`): effectively unchanged — new default `pit_cutoff = filed_8k ≈ now`, so peer/macro/guidance windows match old live-mode output to within seconds.
  - **Manual CLI runs against historical accessions** (`--predict`/`--learn` without `--pit`): behavior DOES change — they now become PIT-safe by default instead of silently live-built. This is the intended correction (old behavior was the bug we're fixing).
  - **Intentional live-mode on a historical accession** ("what would we predict today about this 2023 event?"): now requires the new `--live` flag to preserve old behavior.
  - **Lesson-PIT (T1.5b) read path**: truly unchanged in production — `pit_cutoff=None` bypasses the filter entirely.
- **Open verification item before merge**: confirm whether any K8s worker / cron / `sdk_trigger*.py` caller invokes `earnings_orchestrator` without `--pit` in a way that deliberately relies on live mode; those call sites need an explicit `--live` (or documented migration) before T1.5a ships. Audit target: any use site of `earnings_orchestrator.py main()` across `k8s/`, `scripts/`, and cron drivers.
- T1 / T2 / T3 (below) are not technically code-blocked by T1.5, but running them against a PIT-poisoned corpus produces misleading signal. Recommend: T1.5 first, then corpus re-run, then T1/T2/T3 against honest baseline.

#### Rollout sequence

1. ✅ **T1.5a + T1.5b code** — bundle-PIT default + `--live` opt-in flag + XOR guard (T1.5a); entry schema stamping + reader filter across all four scopes + two new observability counters (T1.5b); datetime-aware `_passes_pit` comparison (post-external-review fix for mixed-offset correctness). Landed in commit `1b79614` (bundled with external-harvester work; PIT work not referenced in that commit message).
2. ✅ **T1.5 tests + this plan section** — 27 new tests (R17a–f + R17_legacy + R18a–f) + Status/Tests/Rollout documentation. Landed in commit `fe0326a`.
3. ⏳ **Corpus wipe** — fresh backup + wipe of `earnings-analysis/learnings/` (new backup timestamp; old `learnings.backup.1776447824` retained). Task #356. Not started.
4. ⏳ **Re-run** — via existing `/tmp/rerun_master.sh` (unchanged — orchestrator default handles PIT automatically). 3 AVGO quarters minimum; full 15 if committing to T4.
5. ⏳ **T4 A/B measurement** — becomes possible against an honest baseline.

#### What does NOT change

- SKILL.md contracts for learner or predictor (attribution_result.v2 top-level fields are already `filed_8k` + `pit_cutoff`; no new learner output contract).
- `validate_attribution.py` V-rules (T1.5b's new fields are storage-layer metadata — see "Schema note" above).
- Concurrency / atomic-write / `fcntl.flock` semantics in `append_global_lessons`.
- Lesson-PIT read path for live-mode callers — `pit_cutoff=None → no filter` branch preserves current production semantics exactly.
- Existing 62+ test suite.
- The `learner-edits.md` schema-structured-routing fix from 2026-04-17 — T1.5 is strictly additive to that work.

> ⚠ Explicit non-invariant: the bundle-PIT default in T1.5a DOES change behavior for manual CLI callers that invoke `--predict`/`--learn` on historical accessions without `--pit`. This is intentional — the old behavior is the root cause of the corpus PIT poisoning. Callers that intentionally want live-mode against a historical accession must now pass `--live`. See "Behavior changes by caller type" in Corpus implications above.

---

### 🔴 Next up — highest EV, **blocked on T1.5 shipping + corpus re-run**

| # | Item | Summary | Where to start |
|---|---|---|---|
| T1 | **Template-overfit mitigation — "labeled lesson consumption"** | Predictor labels each prior lesson as `confirmed` / `contradicted` / `irrelevant` with a bundle-evidence citation BEFORE using it in the directional call. Only `confirmed` lessons may influence direction. Directly attacks the empirically-observed 3-of-15-quarter overfit pattern that the routing fix alone cannot solve. | Full design already in this file — §13 Phase 4 subsection "Proposed mitigation for template overfit — labeled lesson consumption". Predictor SKILL.md + additive `lesson_labels[]` field on `prediction_result.v1` + offline audit script. |
| T2 | **Populate `guidance_history.series`** — structured guidance extraction | 100% of calibration quarters currently have `series = []`; predictor is inferring guide-vs-consensus from press-release prose. Plausibly higher EV than any lesson-routing change: lessons cannot compensate for missing structured fields. | New builder or enrichment on top of existing guidance pipeline. Trace `build_guidance_history` flow; populate `series` from XBRL/transcript/8-K fields. |
| T3 | **Fix `builder_adapters.build_8k_packet` to populate `sector` at source** | Legacy builder returns `sector=None` on 100% of bundles, making `_lookup_company_sector` fallback in `build_prediction_bundle` load-bearing rather than defensive. | Trace delegation to `warmup_cache.build_8k_packet` and add sector-stamping. When fixed, `_lookup_company_sector` becomes truly optional and can be scoped to the write-side `source_sector` stamp only. |

### 🟡 Backlog — tracked, post-re-run or opportunistic

| # | Item | Summary | Where to start |
|---|---|---|---|
| T4 | **Fresh WITH-vs-WITHOUT A/B evaluation** after the full 15-quarter re-run | Two confounds block an honest measurement today: (1) BURL A/B used Opus 4.6/high vs AVGO/NVDA on 4.7/xhigh, and (2) **the entire existing corpus is PIT-poisoned** — every prediction was made with 2026 peer/macro/guidance data against 2023–2024 events (see T1.5 above). A/B can only produce honest signal after **T1.5a+b ship → corpus wipe → full 15-quarter re-run completes with PIT-safe defaults**. Required before any claim that "the learner helps prediction." | `scripts/run_avgo_ab_sequential.py` / `run_nvda_ab_sequential.py` / `run_burl_ab_sequential.py` against the new post-wipe, post-T1.5 data. |
| T5 | **obsidian_thinking.md ship coordination** | When that plan lands, it renames `validate_attribution.py` → `validate_learning.py`, `validate_attribution_output.py` → `validate_learning_output.py`, `attribution/` dir → `learning/`, `finalize_attribution_result` → `finalize_learning_result`, etc. | Mechanical ~15-min `sed`-style pass against the rename table in `learner-edits.md` §0. No logical conflict — learner-edits ships first. |
| T6 | **Predictor-side of labeled consumption** (completes T1) | Strict follow-on to T1 — the predictor emits `lesson_labels[]`, the validator enforces the three-value enum on `label`, and an offline `audit_lesson_labels()` utility flags `confirmed`-rate > 70% as potential rubber-stamping. | Treat as the same PR as T1 (they're one deliverable split across learner + predictor skills). |
| T7 | **CI workflow — `.github/workflows/`** | Add a minimal `pytest` workflow that runs `test_validate_attribution.py`, `test_learning_context.py`, and `test_canonical_sectors_consistency.py` on every PR. Today's enforcement is pre-commit-checklist-only (operator-dependent). | ~30-line YAML. Low priority until repo starts seeing more contributors. |
| T8 | **Audit of learner scope-choice adherence** | Offline audit after 2+ weeks of post-migration data: did the learner ever under-route a sector-wide lesson as cross_ticker (would have been sector-eligible but got narrow routing instead)? Exclusion counters in the observability log are the primary signal. | Simple jq/grep over log archive + global.json. Observational, not intervention — unless patterns emerge. |
| T9 | **Industry-level routing** (finer than the 11-sector enum) | `semiconductors` as a subset of `Technology`, etc. Requires new `Industry` enum + corresponding validator checks. | Deferred until demand emerges. Current granularity is sufficient for 3-ticker calibration. |
| T10 | **Confidence-drift monitoring** | Track WITH-lessons confidence delta vs WITHOUT per quarter. BURL Q3_2025 flagged this (WITH=62 vs WITHOUT=58 on a wrong call = lessons inflated a losing bet). | Offline script over `prediction_result.v1` files. Most useful after T1 lands. |
| T11 | **Template-overfit rate monitoring** | After T1 lands and `lesson_labels[]` is populated, track the rate at which prior lessons match a quarter's outcome vs. how often the predictor applies them. High `confirmed`-rate with low hit-rate = rubber-stamping. | Offline audit leveraging T1's structured labels. |
| T12 | **SKILL.md frontmatter-vs-runtime drift note** | Add one-line note in `.claude/skills/earnings-learner/SKILL.md` clarifying that frontmatter (`model: opus`, `effort: high`) is documentation-only; authoritative runtime source is `config/llm_models.py::LEARNER`. | Trivial prose edit. Prevents future-editor confusion. |
| T13 | **Hindsight contamination audit** — label-only LLM as alternative | Structural risk: the learner sees the realized return and may construct post-hoc narratives that look predictive but aren't. Separate label-only LLM seeing only `(lesson, bundle)` without the outcome would remove this bias. | Design sketch in §13 Phase 4 "Alternative if labels are dishonest". Reserve for the `>85%` rubber-stamp failure mode. |
| T14 | **`data_lessons` signal split** | Learner's `data_lessons` currently conflates "fetch X" (bundle-builder work) vs "weight X more" (predictor-reasoning work). These are different interventions. | Split into two fields in `attribution_result.v2`, or route separately at read time. Minor contract tightening. |
| T15 | **`magnitude_error_pct` semantics for `no_call`** | SKILL.md says use `\|actual_daily_stock_pct\|` when predicted_direction is `no_call`; validator doesn't enforce. | Add validator branch. Rare code path. |
| T16 | **Dotted / hyphenated tickers** (`BRK-B`, `BF-B`) | Validator's `_ok_ticker` rejects them via `.isalpha()`. Not in 796-universe today. | Relax `_ok_ticker` if universe expands. |
| T17 | **Thinking-token capture for audit** | Enable `include_partial_messages=True` on SDK options to capture extended-thinking blocks for label-honesty auditing (most useful post-T1). | One SDK-option flip + a capture pipeline. Non-blocking. |
| T18 | **PIT tier-3 non-stationarity** | Most-recent-quarter learner uses `invocation_time` cutoff → re-running an old last-quarter at a different time yields different attribution. Design tradeoff documented in §3. | Revisit only if observed downstream effect emerges. |
| T19 | **Lesson refinement vs replacement (predictor-side)** | ticker.json is upsert-by-quarter now, but predictor still sees older-but-preserved lessons alongside newer corrective ones. Instruct predictor (in SKILL.md) to prefer newer corrective lessons when they reference the same mechanism. | Predictor SKILL.md instruction, adjacent to T1. |
| T20 | **Event-time graph state for peer selection + sector lookup** (T1.5c residual) | Three residual PIT holes that persist after T1.5a+b ship: (a) `peer_earnings_snapshot.py` Cypher selects peers via current `BELONGS_TO` Industry edges and ranks by current `peer.mkt_cap` — peer SET is today's membership, not event-time; (b) `_lookup_company_sector` returns current sector, affecting sector-lesson matching and `source_sector` stamping; (c) write-side `source_sector` on new entries is today's sector, not event-time. Practical impact for AVGO/NVDA/BURL is small (stable classifications); systemically real for cohort expansion across sector reclassifications, IPOs, delistings, and M&A. | Requires timestamped company-industry edges + historical `mkt_cap` series + event-time sector resolution in Neo4j. Tier-3; revisit when cohort expands beyond semiconductors/retail or when post-reclass ticker enters the universe. |

### 🗑️ Declined — documented in `learner-edits.md` Appendix C

For the record (not actionable): same-sector fallback for cross_ticker routing, dual-read migration mode, concrete worked examples in SKILL.md, keeping `scope_key` as vestigial display field, schema version bump for `global_lessons.v1`→v2. See `learner-edits.md` Appendix C for the full rationale per rejected alternative.

---

## Calibration Artifacts Index (session of 2026-04-16 / 2026-04-17)

Navigation aid for reviewing every prediction + attribution pair produced in this session across 3 tickers × 5 quarters = **15 quarter-level A/B runs**.

**Path convention** (relative to repo root): `earnings-analysis/Companies/{TICKER}/events/{QUARTER}/`

For each quarter, three artifact kinds exist:

| Kind | Relative path inside quarter dir | What it contains |
|---|---|---|
| **WITH-lessons prediction** | `prediction/result.json` | predictor output using the prior lessons bundle |
| **WITHOUT-lessons prediction** (A/B baseline) | `experiments/prediction_no_lessons/result.json` | re-predicted with `learning_context` blanked |
| **Attribution / learner output** | `learning/result.json` | post-event causal diagnosis; source of new lessons |
| Context bundle (input to predictor) | `prediction/context_bundle.json` + `context_bundle_rendered.txt` | what the predictor read |

### AVGO — Opus 4.7 + `effort=xhigh` — 5 quarters

| Q | Actual daily | WITH | WITHOUT | Notable |
|---|---|---|---|---|
| Q1_FY2023 | +5.54% (long) | short(42) ✗ | no_call(28) ✗ | both wrong; first quarter, no ticker lessons yet |
| Q2_FY2023 | +2.87% (long) | long(52) ✓ | short(58) ✗ | lessons helped (DIFF) |
| Q3_FY2023 | −5.38% (short) | long(40) ✗ | short(58) ✓ | **template overfit** (AVGO ticker lesson from Q1/Q2 over-applied) |
| Q4_FY2023 | +2.61% (long) | long(65) ✓ | long(62) ✓ | both right |
| Q1_FY2024 | −6.99% (short) | short(55) ✓ | short(48) ✓ | both right |

**A/B result**: WITH 3/5 (60%), WITHOUT 3/5 (60%), Delta 0. Summary: `earnings-analysis/test-outputs/ab_baseline_AVGO.json`

### NVDA — Opus 4.7 + `effort=xhigh` — 5 quarters

| Q | Actual daily | WITH | WITHOUT | Notable |
|---|---|---|---|---|
| Q4_FY2023 | +14.02% (long) | long(68) ✓ | long(62) ✓ | SAME |
| Q1_FY2024 | +24.37% (long) | long(82) ✓ | long(82) ✓ | IDENTICAL confidence |
| Q2_FY2024 | +0.08% (long) | long(72) ✓ | long(62) ✓ | direction right, magnitude overshot |
| Q3_FY2024 | −2.46% (short) | long(45) ✗ | long(58) ✗ | both wrong (SAME — bundle misread, not lesson overfit) |
| Q4_FY2024 | +16.40% (long) | long(70) ✓ | long(72) ✓ | SAME |

**A/B result**: WITH 4/5 (80%), WITHOUT 4/5 (80%), Delta 0. Summary: `earnings-analysis/test-outputs/ab_NVDA.json`

### BURL — Opus 4.6 + `effort=high` — 5 quarters (most recent 5 events)

| Q | Actual daily | WITH | WITHOUT | Notable |
|---|---|---|---|---|
| Q4_FY2024 | +8.54% (long) | short(55) ✗ | short(55) ✗ | SAME — bundle misread (guide-below-consensus dominated) |
| Q1_FY2025 | −4.54% (short) | long(52) ✗ | short(55) ✓ | **template overfit** (Q4 "compressed spring" lesson over-applied) |
| Q2_FY2025 | +5.28% (long) | long(58) ✓ | long(55) ✓ | SAME |
| Q3_FY2025 | −12.16% (short) | long(62) ✗ | long(58) ✗ | SAME — tail miss, both fooled by sandbagging analog |
| Q4_FY2025 | +6.72% (long) | long(68) ✓ | long(62) ✓ | SAME |

**A/B result**: WITH 2/5 (40%), WITHOUT 3/5 (60%), Delta −1. Summary: `earnings-analysis/test-outputs/ab_BURL.json`

### Cross-run totals

- **WITH lessons**: 9/15 correct (60%)
- **WITHOUT lessons**: 10/15 correct (67%)
- **Delta**: −1 — break-even-to-slightly-negative at n=15; within LLM variance

### Ticker lesson banks (accumulated across sequential runs)

| Path | Description |
|---|---|
| `earnings-analysis/learnings/ticker/AVGO.json` | 5 lessons accumulated over AVGO A/B |
| `earnings-analysis/learnings/ticker/NVDA.json` | 5 lessons accumulated over NVDA A/B |
| `earnings-analysis/learnings/ticker/BURL.json` | 5 lessons accumulated over BURL A/B |
| `earnings-analysis/learnings/global.json` | Cross-ticker lessons (observations marked `affects_all_tickers: true`) |

### Config used per run (for reviewer context)

| Ticker | Dates run | SDK | Model | Effort | Notes |
|---|---|---|---|---|---|
| AVGO | 2026-04-16 | `claude-agent-sdk==0.1.44` | `claude-opus-4-7` | `xhigh` | Used `cli_path=<system CLI v2.1.112>` workaround |
| NVDA | 2026-04-16 | `claude-agent-sdk==0.1.44` | `claude-opus-4-7` | `xhigh` | Same workaround as AVGO |
| BURL | 2026-04-16 | `claude-agent-sdk==0.1.44` | `claude-opus-4-6` | `high` | Briefly reverted to 4.6 before SDK upgrade |
| **Current prod** | 2026-04-17 onward | `claude-agent-sdk==0.1.61` | `claude-opus-4-7` | `xhigh` | Bundled CLI v2.1.112; no workaround needed |

### Known-finding flags for quick navigation

- **Template-overfit cases** (reference for "labeled lesson consumption" mitigation decision in §10):
  - AVGO Q3_FY2023 — `Companies/AVGO/events/Q3_FY2023/learning/result.json`
  - BURL Q1_FY2025 — `Companies/BURL/events/Q1_FY2025/learning/result.json`
- **Learner self-correction examples** (quarter after an overfit where the learner scoped the prior rule):
  - AVGO Q4_FY2023 lesson scoping the Q1/Q2 AI-narrative template
  - BURL Q2_FY2025 lesson scoping the Q4 "compressed spring" rule to clean-beats only

### Caveat (read before drawing conclusions)

All 15 quarters had **`guidance_history.series = []`** (structured guidance extraction not yet populated). The predictor had to infer guide-vs-consensus deltas from free-text press releases rather than structured fields. Fixing this is likely higher-EV than any lesson-consumption mitigation. See §11 "Proposed mitigation for template overfit" for the design of the mitigation before implementation.

---

## 1. Purpose

The earnings learner (`/earnings-learner`) is the post-event causal attribution module. It explains **why** a stock moved after an 8-K earnings filing, compares the realized move against the prediction, and produces reusable lessons that improve future predictions.

**It is NOT**: a predictor, a planner, a trade execution component, or a parameter tuner.

**End goal**: Every lesson the learner writes should make the predictor measurably better at the next quarter's call. The entire design serves this single objective.

**Learning type**: In-context learning only (Type 1). The predictor sees accumulated lessons as part of its context bundle. No parameter auto-tuning (Type 2) is in scope.

---

## 2. Trigger & Timing

### Historical mode
Learner runs sequentially after prediction for each quarter within a ticker's historical bootstrap:
```
Q(n) prediction → Q(n) learner → Q(n+1) prediction → Q(n+1) learner → ...
```
Q(n) learner **must** complete before Q(n+1) prediction starts, ensuring U1 feedback is available.

**Historical failure policy**: If Q(n) learner fails after one retry (no valid `learning/result.json`), the ticker's sequential processing **stops at Q(n)**. It does NOT skip to Q(n+1). The failure is logged for investigation. After the underlying issue is fixed (bad data, unusual filing format, etc.), the ticker can be re-bootstrapped. Other tickers are unaffected. There is no time pressure in historical mode — chain integrity is more important than throughput.

**Live prediction is never blocked**: The live-quarter learner is deferred (§2 Live mode), so live prediction fires regardless of any learner state. The deferred learner runs during the next historical bootstrap, where the historical failure policy above applies.

### Live mode
Live prediction fires immediately on 8-K detection (no learner gate). The live-quarter learner is **deferred** to the next historical bootstrap.

**Why deferred** (was N=35 day timer, replaced): The learner competing with live predictions on the same queue wastes urgent token budget. By deferring to the next historical bootstrap, learners run on the historical queue (batch priority) and the data is richer — 10-Q/10-K and analyst coverage are available by then. Annual quarters (10-K filed 60-90 days after 8-K) are handled naturally without special exceptions.

Detection mechanism:

```
is_historical_done() checks:
  1. event.json quarters all have prediction + attribution result files
  2. live_state.json quarter has attribution if prediction exists
  → Missing attribution returns FALSE → daemon enqueues HISTORICAL
  → Orchestrator sequential processing catches the gap
```

### Hard-fail gates (both modes)
1. `prediction/result.json` must exist — cannot compare without a prediction
2. `daily_stock` return label must exist — cannot attribute without the realized outcome

If either is missing, the learner does NOT run. These are checked by the orchestrator in Python before invocation.

### No source-gating
The learner runs with whatever post-event data is available. Missing sources go into `missing_inputs[]`. Better to write a partial attribution than to block indefinitely.

### Historical bootstrap prerequisites
The historical bootstrap itself is **guidance-gated**: it waits until guidance extraction is completed/failed for all prior quarters. By the time the learner runs for Q(n), all prior guidance and learnings are available. This gating is the daemon/orchestrator's responsibility, not the learner's.

---

## 3. PIT Gating (Information Leakage Prevention)

### The contamination vector
Q(n) learner writes lessons → Q(n+1) predictor reads them. If Q(n) learner saw data from after Q(n+1)'s 8-K filing, those lessons could leak future information into the predictor.

### PIT rule (three-tier)

| Priority | Condition | PIT cutoff |
|----------|-----------|------------|
| 1 | Q(n+1) exists in `get_quarterly_filings()` output | Q(n+1)'s `filed_8k` timestamp |
| 2 | No Q(n+1) in event list, but a live cycle exists (`live_state.json` or fresh 8-K with `daily_stock IS NULL`) | Live quarter's `filed_8k` timestamp |
| 3 | No Q(n+1) and no live cycle | Current invocation time |

For **live learner**: PIT is disabled. All sources are unrestricted.

### PIT enforcement mechanism

PIT is enforced **deterministically** via existing infrastructure, not by prompt instruction alone:

**Neo4j agents**: `[PIT: {pit_cutoff}]` prefix in subagent prompt → agents add WHERE-clause date filters. `pit_gate.py` hook validates every Neo4j read response. If any item has `available_at > PIT`, the hook blocks and the agent retries.

**External sources**: `pit_fetch.py` wrapper handles PIT filtering per source:
```bash
python3 .claude/skills/earnings-orchestrator/scripts/pit_fetch.py \
  --source alphavantage --pit 2024-05-02T16:30:00-04:00 EARNINGS symbol=AAPL
```
Each external item gets `available_at` mapped from provider metadata. Items without verifiable publication timestamps are dropped (fail-closed).

**Source priority for historical runs** (stricter sources first):

| Tier | Sources | PIT mechanism |
|------|---------|---------------|
| 0 (deterministic) | neo4j-report, neo4j-transcript, neo4j-xbrl, neo4j-news, neo4j-entity, neo4j-vector-search | WHERE clause + `pit_gate.py` |
| 1 (PIT-safe APIs) | alphavantage-earnings, yahoo-earnings, bz-news-api | `pit_fetch.py` + `available_at` validation |
| 2 (gap-fill only) | perplexity-ask, perplexity-search, perplexity-reason, perplexity-research | `pit_fetch.py` wraps API directly, excludes synthesis answer in PIT mode |

Historical learner should exhaust Tier 0-1 before using Tier 2. Live learner has no tier restriction.

### Traced example

```
Ticker AAPL, historical bootstrap:
  get_quarterly_filings() returns:
    Q1_FY2024: filed_8k=2024-02-01T16:30
    Q2_FY2024: filed_8k=2024-05-02T16:30
    Q3_FY2024: filed_8k=2024-08-01T16:30
    Q4_FY2024: filed_8k=2024-11-01T16:30
    Q1_FY2025: filed_8k=2025-02-01T16:30

  Sequential processing:
    Q1 prediction (PIT=Q1 filed_8k) → Q1 learner (PIT=Q2 filed_8k: 2024-05-02T16:30)
      → Learner sees: transcript, 10-Q, all news between Q1 and Q2 earnings
      → Learner does NOT see: anything from Q2's 8-K day onward
      → Writes learning/result.json → Python appends to ticker.json, global.json

    Q2 prediction (PIT=Q2 filed_8k, reads Q1 lessons) → Q2 learner (PIT=Q3 filed_8k)
    ...
    Q1_FY2025 prediction → Q1_FY2025 learner (PIT=now, no Q2_FY2025 yet)
```

---

## 4. Inputs

The orchestrator assembles these inputs and passes them to the learner.

**Design choice: no pre-assembled bundle.** Unlike the predictor (which receives a pre-built 8-section bundle), the learner does NOT get a pre-assembled data bundle. The learner is fundamentally different — no speed constraint, multi-turn, follows evidence trails. Pre-assembling a bundle would constrain its investigation. Instead, the learner receives targeted inputs (prediction result, actual returns, metadata) and a **reference** to the predictor's context_bundle.json (to see what the predictor had). The learner then autonomously fetches whatever post-event data it needs via Data SubAgents or direct MCP access.

### Pre-fetched by orchestrator (Python)

| Input | Source | Required |
|-------|--------|----------|
| `prediction/result.json` | Filesystem | **Yes** (hard gate) |
| `actual_return` packet | Neo4j PUBLISHED_AS relationship on 8-K | **Yes** (hard gate, validated before invocation) |
| `prediction/context_bundle.json` path | Filesystem | Yes (reference only — what predictor saw) |
| Quarter metadata: `ticker`, `quarter_label`, `filed_8k`, `accession_8k` | event.json | Yes |
| `pit_cutoff` | Derived from get_quarterly_filings() per §3 rules | Yes (null for live) |
| `pit_mode` | `"historical"` or `"live"` | Yes |
| Prior lessons: `learnings/ticker/{TICKER}.json` path | Filesystem | Yes (may not exist for first quarter) |

### Normalized `actual_return` packet

Orchestrator queries Neo4j and normalizes field names before passing to learner:

```json
{
  "daily_stock_pct": -5.28,
  "hourly_stock_pct": -3.12,
  "session_stock_pct": -4.1,
  "daily_macro_pct": -0.5,
  "daily_sector_pct": -1.2,
  "daily_industry_pct": null,
  "market_session": "after_hours"
}
```

Field mapping from Neo4j: `daily_stock` → `daily_stock_pct`, `hourly_stock` → `hourly_stock_pct`, `daily_macro` → `daily_macro_pct`, etc. Null when the relationship property is absent.

### Self-fetched by learner (Data SubAgents)

The learner autonomously queries additional sources using PIT-enabled Data SubAgents. Available sources:

**Neo4j (Tier 0)**:
- `neo4j-report` — 8-K filing details, exhibits (EX-99.1), return data
- `neo4j-transcript` — Earnings call transcript, prepared remarks, Q&A exchanges
- `neo4j-xbrl` — 10-Q/10-K financial statement data (EPS, revenue, margins, segments)
- `neo4j-news` — News articles with channel filtering (earnings, analyst, corporate, legal, notable) and stock return impact
- `neo4j-entity` — Company info, price series, dividends, splits, sector/industry
- `neo4j-vector-search` — Semantic search across news and transcript Q&A

**External APIs (Tier 1)**:
- `alphavantage-earnings` — Consensus estimates, actuals, earnings calendar
- `yahoo-earnings` — Earnings history, analyst ratings/price targets, upgrades/downgrades
- `bz-news-api` — Benzinga news with channel-filtered pre/post-event coverage

**Web/Research (Tier 2 — historical gap-fill only, live unrestricted)**:
- `perplexity-ask` — Quick factual Q&A with citations
- `perplexity-search` — Web search for analyst commentary, market reactions
- `perplexity-reason` — Multi-step reasoning for complex attribution
- `perplexity-research` — Deep investigation (live only, or rare historical gap-fill)

The learner should investigate exhaustively within its max_turns guardrail (40-50 turns). It is free to query any source, follow leads, and iterate until confident in its attribution.

---

## 5. What the Learner Does

### Five-phase workflow

**Phase 1 — Load Context**
1. **Read prediction + actuals**: Load `prediction/result.json` and `actual_return` to establish the gap (what was predicted vs what happened)
2. **Scan prediction context bundle**: Read `prediction/context_bundle.json` to understand what data the predictor had access to. Essential for distinguishing "predictor never had this signal" (→ data_lessons: "fetch X") from "predictor had it but underweighted it" (→ data_lessons: "weight X more")
3. **Read prior lessons**: Load `learnings/ticker/{TICKER}.json` if it exists — review own prior advice for refinement

**Phase 2 — Investigate**
4. **Fetch post-event evidence** via PIT-gated Data SubAgents (or direct MCP). Exhaust Tier 0-1 before Tier 2. Sources:
   - Earnings transcript Q&A (what did analysts focus on? what did management hedge on?)
   - 10-Q/10-K XBRL actuals (margin trends, segment breakdowns, cash flow changes)
   - Post-event news (analyst reactions, upgrades/downgrades, rating changes)
   - Pre-event news (expectations setup, channel-filtered for earnings/analyst/corporate)
   - Entity data (inter-quarter price action, dividends, splits)
   - Consensus verification (AlphaVantage for historical; Perplexity for live)
   - Peer/sector reactions (same-sector companies' returns around the event)

**Phase 3 — Attribute**
5. **Identify primary driver** and contributing factors — each with `summary`, `category`, and `evidence_refs` (ledger IDs)
6. **Compare predicted vs actual**: What worked, what failed, and why — populate `prediction_comparison`

**Phase 4 — Distill Lessons**
7. **Write predictor lessons**: Capped (≤3), specific, actionable — how should the predictor reason differently?
8. **Write data lessons**: Capped (≤3) — what data signals should the predictor have fetched or weighted more heavily?
9. **Write global observations**: Sector, macro, or cross-ticker insights (0-3 entries)
10. **Refine prior lessons**: If prior advice was too vague or misdirected, write a more specific replacement in this quarter's entry

**Phase 5 — Finalize**
11. **Record gaps**: Any unavailable sources go to `missing_inputs[]`
12. **Write `learning/result.json`**: Single output file containing all of the above. Python handles derived writes (ticker.json, global.json).

### Key principles

- **Evidence-based claims only**: Every attribution claim must cite a source in the evidence ledger. No unsourced assertions.
- **Causal, not correlational**: The primary driver should explain the mechanism (e.g., "guidance cut overshadowed EPS beat because forward outlook worsened by -8.2%"), not just note co-occurrence.
- **Lesson specificity**: "Weight guidance more" is too vague. "When management narrows guidance range downward while EPS beats, guidance dominates for this ticker (3/4 quarters)" is actionable.
- **Generalizability guardrail**: Lessons must be reusable across future quarters. No quarter-specific command rules (e.g., NOT "in Q3 FY2024 always go short on NOG"). Lessons are advisory soft priors, not hard rules. The learner converts findings into guidance that improves predictor behavior without overfitting to a single event.
- **Predictor-facing output**: Everything the learner writes should be optimized for making the NEXT prediction better. Forensic detail exists for audit, but lessons exist for improvement.
- **Caps enforce signal quality**: The learner must prioritize the most important observations rather than dumping everything. Capped arrays force ruthless prioritization.

---

## 6. Output Contract: `learning/result.json`

**Schema version**: `attribution_result.v2`
**File path**: `earnings-analysis/Companies/{TICKER}/events/{quarter_label}/learning/result.json`

### Full schema

```json
{
  "schema_version": "attribution_result.v2",
  "ticker": "AAPL",
  "quarter_label": "Q1_FY2025",
  "filed_8k": "2025-05-01T16:30:00-04:00",
  "accession_8k": "0000320193-25-000055",
  "attributed_at": "2026-04-16T14:30:00-04:00",
  "model_version": "claude-opus-4-6",
  "pit_mode": "historical",
  "pit_cutoff": "2025-07-31T16:00:00-04:00",
  "pit_boundary_source": "next_quarter",

  "actual_return": {
    "daily_stock_pct": -5.28,
    "hourly_stock_pct": -3.12,
    "session_stock_pct": -4.1,
    "daily_macro_pct": -0.5,
    "daily_sector_pct": -1.2,
    "daily_industry_pct": null,
    "market_session": "after_hours"
  },

  "evidence_ledger": [
    {"id": "E1", "claim": "EPS Actual", "value": "$1.65", "source": "8K:EX-99.1", "date": "2025-05-01"},
    {"id": "E2", "claim": "EPS Consensus", "value": "$1.63", "source": "AlphaVantage:EARNINGS", "date": "pre-filing"},
    {"id": "E3", "claim": "Tariff Cost Guidance", "value": "$900M for Q3", "source": "Transcript:PreparedRemarks", "date": "2025-05-01"},
    {"id": "E4", "claim": "Gross Margin Guidance Cut", "value": "-60 to -160 bps", "source": "8K:EX-99.1", "date": "2025-05-01"},
    {"id": "E5", "claim": "Greater China Revenue", "value": "$16.0B vs $16.4B PY (-2.3% YoY)", "source": "8K:EX-99.1", "date": "2025-05-01"},
    {"id": "E6", "claim": "Analyst Reaction — Goldman", "value": "Downgraded to Neutral", "source": "News:AnalystRatings", "date": "2025-05-02"}
  ],

  "primary_driver": {
    "summary": "$900M tariff cost warning — first quantification by management, drove gross margin guidance cut",
    "category": "guidance_change",
    "evidence_refs": ["E3", "E4"]
  },

  "contributing_factors": [
    {
      "summary": "Greater China revenue decline continuing 3-quarter deceleration trend",
      "category": "segment_performance",
      "evidence_refs": ["E5"]
    },
    {
      "summary": "Post-earnings analyst downgrades amplified negative sentiment",
      "category": "analyst_sentiment",
      "evidence_refs": ["E6"]
    }
  ],

  "feedback": {
    "prediction_comparison": {
      "predicted_direction": "long",
      "predicted_confidence_score": 72,
      "predicted_move_range_pct": [2.0, 5.0],
      "predicted_key_drivers": ["Services revenue momentum", "EPS beat expectations"],
      "actual_direction": "short",
      "direction_correct": false,
      "magnitude_error_pct": 7.28,
      "comment": "Overweighted EPS beat, missed tariff cost quantification as dominant driver"
    },
    "what_worked": [
      "EPS beat direction correctly identified from strong Services momentum"
    ],
    "what_failed": [
      "Missed tariff cost quantification as primary driver — management had not quantified before this call",
      "Underweighted Greater China deceleration despite 3-quarter declining trend"
    ],
    "why": "Predictor had no signal on tariff cost magnitude (first-time disclosure). Post-event transcript and EX-99.1 revealed this as the dominant market narrative, confirmed by analyst downgrades next day.",
    "predictor_lessons": [
      "When macro trade tensions are elevated, weight management cost-impact commentary over EPS beat magnitude — first-time quantifications often dominate reactions",
      "Greater China revenue trajectory shows 3-quarter structural decline — treat as ongoing headwind, not one-time miss"
    ],
    "data_lessons": [
      "Fetch sector peer tariff exposure data (MSFT/GOOG tariff guidance) to calibrate tariff risk severity — peer context was absent from prediction bundle",
      "Weight Transcript Q&A analyst focus areas: 6/10 questions targeted tariff impact, signaling market concern the predictor missed"
    ]
  },

  "global_observations": [
    {
      "scope": "sector",
      "target_sector": "Technology",
      "lesson": "..."
    },
    {
      "scope": "macro",
      "lesson": "..."
    }
  ],
  // Amended 2026-04-17: scope_key REMOVED; routing is via target_sector
  // (sector scope) or related_tickers (cross_ticker scope). Shape-only
  // placeholder `lesson` text per learner-edits.md §6.7 — do not copy.

  "missing_inputs": ["10-K"],

  "data_sources_used": [
    "neo4j-report", "neo4j-transcript", "neo4j-news",
    "neo4j-xbrl", "neo4j-entity", "alphavantage-earnings"
  ],

  "context_bundle_ref": "prediction/context_bundle.json",
  "prediction_result_ref": "prediction/result.json"
}
```

### Field reference

| Field | Required | Notes |
|-------|----------|-------|
| `schema_version` | Yes | `"attribution_result.v2"` |
| `ticker`, `quarter_label`, `filed_8k`, `accession_8k` | Yes | Event identifiers (match prediction) |
| `attributed_at` | Yes | ISO timestamp when attribution completed |
| `model_version` | Yes | Model that ran the attribution |
| `pit_mode` | Yes | `"historical"` or `"live"` |
| `pit_cutoff` | Yes | ISO timestamp or `null` (live mode) |
| `actual_return` | Yes | Normalized return packet (§4) |
| `evidence_ledger` | Yes | Array of `{id, claim, value, source, date}`. Every numeric or factual assertion cited here. Required non-empty for any valid attribution. |
| `primary_driver` | Yes | `summary` (free text) + `category` (snake_case string, see below) + `evidence_refs` (array of ledger IDs). Drivers may cite current-quarter filings, prior-quarter filings, peer returns, transcript passages, predictor context bundle evidence, and post-event coverage — but every cited claim must resolve to a ledger ID. |
| `contributing_factors` | Yes | Array (max 3, same shape as primary_driver). Can be `[]`. |
| `feedback` | Yes | Nested block — see below |
| `global_observations` | Yes | Array (max 3), scope-conditional shape per `.claude/plans/learner-edits.md` §4.1: `{scope:"sector", target_sector, lesson}` / `{scope:"macro", lesson}` / `{scope:"cross_ticker", related_tickers, lesson}`. `scope_key` REMOVED (amendment 2026-04-17 — validator rejects). Can be `[]`. Python upserts these into `global.json` by `(source_ticker, quarter_label)`. |
| `missing_inputs` | Yes | Array of canonical strings. Can be `[]`. |
| `data_sources_used` | Yes | Array of agent names actually queried |
| `context_bundle_ref` | Yes | Relative path to prediction's context bundle |
| `prediction_result_ref` | Yes | Relative path to prediction result |
| `pit_boundary_source` | Yes | `"next_quarter"`, `"live_cycle"`, or `"invocation_time"` — which §3 tier determined the PIT cutoff |

**Feedback block caps:**

| Field | Max | Purpose |
|-------|-----|---------|
| `prediction_comparison` | 1 object | Predicted vs actual comparison. Fields copied from `prediction/result.json`: `predicted_direction` (← `direction`), `predicted_confidence_score` (← `confidence_score`), `predicted_move_range_pct` (← `expected_move_range_pct`), `predicted_key_drivers` (← `key_drivers`). `actual_direction` derived from `daily_stock_pct` sign (positive = long, negative = short). `magnitude_error_pct` = distance from `actual_daily_stock_pct` to nearest bound of directionally-signed predicted range; 0 if actual is within range. Example: predicted long [+2.0, +5.0], actual -5.28% → nearest bound +2.0 → \|(-5.28) - 2.0\| = 7.28. |
| `what_worked` | 2 items | What the predictor got right (prevents over-correction) |
| `what_failed` | 3 items | Where the prediction went wrong |
| `why` | 1-3 sentences | Causal context explaining the gap |
| `predictor_lessons` | 3 items | How to reason differently next time (soft priors) |
| `data_lessons` | 3 items | What data to seek or weight more heavily. Covers both "fetch X" (predictor never had it — confirmed by scanning context_bundle.json) and "weight X more" (predictor had it but underweighted it) |

Caps enforce signal quality. Required arrays may be empty when no valid item exists; do not add filler. All lesson fields (`predictor_lessons`, `data_lessons`, `global_observations`) must be generalizable heuristics reusable across future quarters — not quarter-specific commands (see Generalizability guardrail in §5).

**Driver `category` field**: Free-form snake_case label for the dominant reaction mechanism. Advisory for grouping and pattern analysis only — `summary` + `evidence_refs` remain authoritative. Use a familiar label when it cleanly fits. Otherwise create a precise new snake_case label (e.g., `credit_loss_reserve_build`, `fleet_utilization`, `subscriber_churn`). If several mechanisms matter, choose the one that best explains the market reaction and capture the rest in `summary` or `contributing_factors`. Do not validate against a fixed enum.

Illustrative example labels (non-exhaustive):

| Label | Typical use |
|-------|-------------|
| `eps_surprise` | EPS beat or miss was dominant |
| `revenue_surprise` | Revenue beat or miss was dominant |
| `guidance_change` | Forward guidance raise, cut, narrowing, or maintained |
| `margin_shift` | Gross/operating/net margin expansion or compression |
| `segment_performance` | Specific segment strength/weakness (geo, product, business unit) |
| `macro_environment` | Macro conditions dominated (rates, trade, geopolitical) |
| `sector_momentum` | Sector-wide move, not company-specific |
| `management_action` | Leadership change, restructuring, M&A, capital allocation |
| `analyst_sentiment` | Analyst upgrades/downgrades, target revisions |
| `product_cycle` | Product launch, delay, demand signals |
| `regulatory` | FDA, antitrust, trade tariff, compliance |
| `clinical_trial_readout` | Biotech: trial data release |
| `nim_compression` | Banks: net interest margin change |
| `occupancy_decline` | REITs: occupancy or same-store metrics |
| `production_guidance` | Energy/industrials: output volume guidance |

If none of these fit, coin a precise new label — there is no `other` category.

**Canonical `missing_inputs` values:**
`transcript`, `10-Q`, `10-K`, `presentation`, `post_event_news`, `peer_reactions`, `sector_context`, `xbrl_actuals`

### Changes from `attribution_result.v1` (master plan §2d)

| Change | Rationale |
|--------|-----------|
| Dropped `surprise_analysis` | Predictor already computes EPS/revenue/guidance surprise |
| Dropped `analysis_summary` | Machine-readable output; causal narrative captured in `primary_driver.summary` + `feedback.why` |
| Replaced `planner_lessons` with `data_lessons` | Planner removed from pipeline; data lessons cover both "fetch this" and "weight this more" |
| Added `evidence_ledger` with ID refs | Centralized citations, no duplication across driver sections |
| Added `pit_mode`, `pit_cutoff` | Audit: which PIT boundary was enforced |
| Expanded `actual_return` | Added `session_stock_pct`, `daily_macro_pct`, `daily_sector_pct`, `daily_industry_pct` |
| Added `accession_8k` | Direct filing identifier for audit |
| Added `pit_boundary_source` | Audit: which §3 tier determined PIT cutoff (`next_quarter`, `live_cycle`, `invocation_time`) |
| Added `global_observations[]` | Learner writes cross-ticker insights here; Python extracts and appends to `global.json` |
| Write ownership: learner writes only `result.json` | Python orchestrator handles `ticker.json` and `global.json` appends — safer for atomic writes and concurrent ticker processing |
| `predicted_confidence` → `predicted_confidence_score` | Aligned with predictor contract field name `confidence_score` |

---

## 7. Ticker Lessons: `learnings/ticker/{TICKER}.json`

**File path**: `earnings-analysis/learnings/ticker/{TICKER}.json`
**Write mode**: Append-only. The learner does NOT write this file. The orchestrator Python extracts feedback from `learning/result.json` and atomically appends one entry to the `lessons[]` array.
**Read-time cap**: `build_learning_context()` selects the most recent **8 entries** for predictor context.

### Schema

```json
{
  "schema_version": "ticker_lessons.v1",
  "ticker": "AAPL",
  "updated_at": "2026-04-16T14:30:00-04:00",
  "lessons": [
    {
      "quarter_label": "Q4_FY2024",
      "attributed_at": "2026-03-15T10:00:00-04:00",
      "source_filed_8k": "2024-11-01T16:30:00-04:00",
      "source_pit_cutoff": "2025-02-01T16:30:00-04:00",
      "direction_correct": true,
      "actual_daily_pct": 3.2,
      "predicted_direction": "long",
      "predicted_confidence_score": 65,
      "primary_driver_summary": "Services revenue acceleration + strong iPhone demand",
      "primary_driver_category": "revenue_surprise",
      "what_worked": ["Revenue beat identification", "Services momentum flagged correctly"],
      "what_failed": [],
      "predictor_lessons": ["Services mix shift increasingly drives AAPL reaction — weight segment breakdown higher than hardware revenue"],
      "data_lessons": [],
      "why": "Direction correct. Confidence was conservative — could have been higher given strong Services signal."
    },
    {
      "quarter_label": "Q1_FY2025",
      "attributed_at": "2026-04-16T14:30:00-04:00",
      "source_filed_8k": "2025-02-01T16:30:00-04:00",
      "source_pit_cutoff": "2025-05-02T16:30:00-04:00",
      "direction_correct": false,
      "actual_daily_pct": -5.28,
      "predicted_direction": "long",
      "predicted_confidence_score": 72,
      "primary_driver_summary": "$900M tariff cost warning — first quantification by management",
      "primary_driver_category": "guidance_change",
      "what_worked": ["EPS beat identified from Services momentum"],
      "what_failed": ["Missed tariff cost as primary driver", "Underweighted China deceleration"],
      "predictor_lessons": [
        "When macro trade tensions elevated, weight management cost-impact commentary over EPS beat",
        "China revenue 3-quarter decline is structural — treat as ongoing headwind"
      ],
      "data_lessons": [
        "Fetch sector peer tariff exposure data for context",
        "Weight Transcript Q&A analyst focus areas — 6/10 questions targeted tariff impact"
      ],
      "why": "Tariff magnitude was unknown pre-filing. When macro regime is adversarial, look harder for management cost quantification in forward guidance."
    }
  ]
}
```

### What goes into each entry

Each entry is a compact extract from `learning/result.json`'s feedback block plus key metadata. It contains exactly the information the predictor needs to learn from this quarter — no evidence ledger, no full analysis. The `primary_driver_category` enables the predictor to see driver-type patterns across quarters (e.g., "guidance_change dominated 3/4 AAPL quarters").

**`source_filed_8k` / `source_pit_cutoff` (T1.5b, 2026-04-17)**: Python-stamped at write time. Copied verbatim from the `filed_8k` + `pit_cutoff` top-level fields on `attribution_result.v2`. Used by the read-side PIT filter in `build_learning_context` — a lesson is visible to a predictor at `predictor.pit_cutoff` iff `source_pit_cutoff <= predictor.pit_cutoff` (chronological, tz-aware). Legacy entries missing these fields are treated as post-cutoff in historical mode (excluded) and passed through in live mode (preserves real-time semantics).

### Lesson refinement

When writing a new entry, the learner reads prior entries and checks:
- Did the predictor follow prior advice? (Compare predicted vs actual against prior predictor_lessons)
- Was prior advice too vague? If so, write a more specific version.
- Was prior advice wrong? If so, explicitly note the correction.

Example refinement:
```
Q3 wrote: "weight China revenue decline"
Q4 predictor still missed China impact
Q4 writes: "China revenue requires 4-quarter trend analysis — deceleration
            from $18B→$17B→$16.4B→$16B shows structural decline, not just
            QoQ miss. Prior lesson was correct but insufficiently specific."
```

---

## 8. Global Lessons: `learnings/global.json`

> **AMENDED 2026-04-17** — the schema below reflects the **structured-routing** contract from `.claude/plans/learner-edits.md`. `scope_key` has been removed; routing is by `target_sector` (sector scope) or `related_tickers` (cross_ticker scope). See `learner-edits.md` §4 for the full authoritative schema and §6.2 for the writer semantics.

**File path**: `earnings-analysis/learnings/global.json`
**Write mode**: Upsert-by-`(source_ticker, quarter_label)` (amendment 2026-04-17 — was "append-only"). The learner does NOT write this file directly. The orchestrator Python extracts `global_observations[]` from `learning/result.json`, enriches each entry with `source_ticker`, `source_sector` (Neo4j lookup), `quarter_label`, and `attributed_at`, and atomically upserts to this file. The upsert purges any prior entries for the same `(source_ticker, quarter_label)` before extending — idempotent under derived-write recovery or any re-run. Concurrency-safe via `fcntl.flock`.
**Read-time cap**: `build_learning_context()` selects up to **4 sector + 4 macro + 2 cross_ticker = 10 entries** filtered per-scope by structured routing fields.

### Schema (amended)

```json
{
  "schema_version": "global_lessons.v1",
  "updated_at": "2026-04-17T14:30:00-04:00",
  "entries": [
    {
      "scope": "sector",
      "target_sector": "Technology",
      "source_ticker": "AAPL",
      "source_sector": "Technology",
      "quarter_label": "Q1_FY2025",
      "attributed_at": "2026-04-17T14:30:00-04:00",
      "source_filed_8k": "2025-02-01T16:30:00-04:00",
      "source_pit_cutoff": "2025-05-02T16:30:00-04:00",
      "lesson": "Tariff cost quantification dominated tech reactions in Q1 FY2025 — management first-time disclosures of cost magnitude were primary drivers across AAPL and MSFT"
    },
    {
      "scope": "macro",
      "source_ticker": "AAPL",
      "source_sector": "Technology",
      "quarter_label": "Q1_FY2025",
      "attributed_at": "2026-04-17T14:30:00-04:00",
      "source_filed_8k": "2025-02-01T16:30:00-04:00",
      "source_pit_cutoff": "2025-05-02T16:30:00-04:00",
      "lesson": "During elevated trade tension regime, forward cost guidance dominates backward-looking EPS beats by ~2x in attribution weight"
    },
    {
      "scope": "cross_ticker",
      "related_tickers": ["AAPL", "MSFT"],
      "source_ticker": "AAPL",
      "source_sector": "Technology",
      "quarter_label": "Q1_FY2025",
      "attributed_at": "2026-04-17T14:30:00-04:00",
      "source_filed_8k": "2025-02-01T16:30:00-04:00",
      "source_pit_cutoff": "2025-05-02T16:30:00-04:00",
      "lesson": "MSFT guided cautiously on Azure capex 2 weeks before AAPL's filing — this was a leading signal for AAPL tariff exposure that the predictor missed"
    }
  ]
}
```

**Removed fields**: `scope_key` (validator rejects across every scope). **Added fields**: `related_tickers` (cross_ticker only, required non-empty UPPER 1–5 char list, max 8, no duplicates), `target_sector` (sector only, required, must be in the 11-value canonical enum from `config/canonical_sectors.py`), `source_sector` (Python-stamped audit metadata — NOT used for routing).

### Scope types (amended)

| Scope | Purpose | Routing field | Validator check |
|-------|---------|---------------|-----------------|
| `sector` | Sector-wide pattern | `target_sector` | Must be one of the 11 `CANONICAL_SECTORS` values |
| `macro` | Regime-wide observation | (none — always included) | Rejects `target_sector` and `related_tickers` |
| `cross_ticker` | Peer/competitor lesson bound to specific tickers | `related_tickers` | Non-empty, UPPER, 1–5 chars each, max 8, no duplicates |

### Guidelines for global entries

- Write 0-3 global entries per attribution. Most quarters will have 1-2.
- Each entry should be a **generalizable observation**, not ticker-specific detail.
- Do NOT write a global entry if the observation is only relevant to this specific ticker — that belongs in ticker.json.
- Keep `lesson` text concise (1-2 sentences). It's a signal, not an essay.

### Why global.json matters for sequential processing

When processing multiple tickers sequentially, global.json accumulates cross-ticker insights:
```
Process AAPL Q2 → learner writes: "Tech: AI capex concerns dominated Q2 reactions"
Process MSFT Q2 → predictor reads global.json → sees AAPL's sector insight → better informed
```

---

## 9. `build_learning_context()` Adapter

> **AMENDED 2026-04-17** — routing is now structured-field based (no regex, no `scope_key` matching). See `.claude/plans/learner-edits.md` §4.3 and §6.3 for the authoritative filter logic and observability contract. The `sector_lookup` callable parameter has been removed from the signature.

**Location**: `scripts/earnings/earnings_orchestrator.py` (not `builder_adapters.py` — this is a lightweight local file read; bundle-level current-ticker sector resolution uses the Neo4j-backed `_lookup_company_sector` fallback when `8k_packet.sector` is None, which is the common case).
**Role**: Read-time compatibility layer that transforms derived lesson files into predictor-ready compact context. Emits one structured-counter log line per call.

### Interface

```python
def build_learning_context(ticker: str, sector: str = None,
                           base_dir: Path = None) -> dict:
    """Build learning context for predictor consumption.

    Reads ticker lessons and global lessons, filters by recency and relevance,
    returns compact context suitable for inclusion in the prediction bundle.
    """
```

### Filtering logic

**Ticker lessons** (`learnings/ticker/{TICKER}.json`):
- Read all entries from `lessons[]`
- Select most recent **8 entries** (by `attributed_at`)
- Return as `ticker_lessons[]`

**Global lessons** (`learnings/global.json`) — AMENDED 2026-04-17:
- Read all entries from `entries[]`
- Filter by structured-field routing (NO regex, NO `scope_key`):
  - `scope=sector` → include iff `_normalize_sector(entry.target_sector) == _normalize_sector(current_sector)`
  - `scope=macro` → always include (regime matters for all tickers)
  - `scope=cross_ticker` → include iff `ticker in entry.related_tickers`
- **No same-sector fallback** for cross_ticker — broad lessons belong in `scope=sector`. See `learner-edits.md` Appendix C "rejected alternatives" for the pollution rationale.
- Every exclusion increments a named counter (`sector_mismatch`, `current_sector_unknown`, `cross_ticker_not_listed`, `cross_ticker_missing_related`, `unknown_scope`, `legacy_schema`). An observability log line fires on every call — even when `global.json` is absent.
- Deduplicate within each scope by normalized lesson text.
- Per-scope cap: max **4 sector** + **4 macro** + **2 cross_ticker** = **10 entries** total
- Sort by recency (`attributed_at`) within each scope bucket before capping.
- Return as `global_lessons[]`

### Output shape

```json
{
  "ticker_lessons": [
    {
      "quarter_label": "Q1_FY2025",
      "direction_correct": false,
      "actual_daily_pct": -5.28,
      "primary_driver_summary": "...",
      "predictor_lessons": ["..."],
      "data_lessons": ["..."],
      "why": "..."
    }
  ],
  "global_lessons": [
    {
      "scope": "sector",
      "target_sector": "Technology",
      "source_ticker": "AAPL",
      "source_sector": "Technology",
      "lesson": "..."
    }
  ],
  "ticker_ref": "earnings-analysis/learnings/ticker/AAPL.json",
  "global_ref": "earnings-analysis/learnings/global.json"
}
```

When neither file exists (first-ever ticker prediction), returns:
```json
{
  "ticker_lessons": [],
  "global_lessons": [],
  "ticker_ref": null,
  "global_ref": null
}
```

### Integration with predictor bundle

`BUNDLE_ITEM_ORDER` remains the 7 parallel builders (Neo4j/API). `learning_context` is the logical 8th bundle field, added after builder execution in `build_prediction_bundle()` as a lightweight file read:

```python
# In build_prediction_bundle(), after parallel builders complete:
bundle["learning_context"] = build_learning_context(ticker, sector=sector)
```

Corresponding renderer `_render_learning_context()` formats ticker + global lessons as Section 10 in the prediction bundle text.

---

## 10. Invocation Pattern — LOCKED

### Decision: Skill authored, SDK main-session executed

The learner is **authored** in `.claude/skills/earnings-learner/SKILL.md` but **executed** in a fresh main-session SDK call — not via `/earnings-learner` fork and not as a Task-spawned agent.

**Why this pattern (validated 2026-04-16):**

| Invocation mode | Data SubAgents accessible | Thinking | Verdict |
|---|---|---|---|
| `/earnings-learner` fork (Skill tool) | 6/14 — neo4j-*, yahoo, bz-news-api are agents not skills | Yes | ❌ Missing 8 critical agents |
| Task-spawned agent (Agent tool) | 0/14 — Agent tool absent from all subagent tiers | No | ❌ No spawning, no thinking |
| **SDK embed (main session)** | **14/14** — Agent tool available (27 built-in tools) | **Yes** (via prompt + SDK options) | ✅ **Production path** |

**How it works:**

```python
# _run_learner_via_sdk() in earnings_orchestrator.py
learner_instructions = load_skill_content("earnings-learner")  # reads SKILL.md, strips frontmatter
prompt = f"{learner_instructions}\n\n--- INPUTS ---\n{assembled_inputs}"

async for msg in query(
    prompt=prompt,
    options=ClaudeAgentOptions(
        model="claude-opus-4-6",           # full model ID (not short "opus")
        effort="high",                      # reasoning depth
        thinking={"type": "adaptive"},      # Claude decides when to use extended thinking
        setting_sources=["project"],        # load project settings (MCP servers, hooks)
        permission_mode="bypassPermissions",
        max_turns=50,                       # safety guardrail, not a target
    ),
):
    ...
```

All SDK options verified against installed `claude_agent_sdk==0.1.44` (2026-04-16). The prompt body should also include "ultrathink" as a belt-and-suspenders instruction alongside the SDK `effort`/`thinking` parameters.

**Model ID pinning (not "latest" aliases)**: The SDK does NOT accept `"opus"` or `"claude-opus-latest"` for `ClaudeAgentOptions.model` — only full version IDs like `"claude-opus-4-7"`. Production code pins to a specific version. Rationale: (1) **audit trail** — the `model_version` field in learning/result.json records exactly which model produced each lesson; (2) **U1 loop integrity** — silently swapping models mid-loop breaks lesson-chain attribution; (3) **validator stability** — new models may shift JSON shapes, and pinning means breakage is caught at version-bump time, not silently. When a new Opus ships, update `PREDICTOR_MODEL_ID` constant and the learner `model=` string (two-line change).

**Current pin: `claude-opus-4-7`** on subscription auth via system CLI. See "Critical: bundled CLI vs system CLI" below.

### Complete `ClaudeAgentOptions` inventory (SDK v0.1.44)

All available parameters, and whether we set them in the predictor/learner SDK calls:

| Parameter | Type | Our value | Rationale |
|-----------|------|-----------|-----------|
| **Auth & model** | | | |
| `model` | str | `"claude-opus-4-7"` | Pinned; see above |
| `fallback_model` | str | not set | Intentional: want failures to surface, not silently downgrade |
| `cli_path` | str/Path | `shutil.which("claude")` | Force system CLI (newer + OAuth; not bundled) |
| `env` | dict | `{"ANTHROPIC_API_KEY": "", "ANTHROPIC_AUTH_TOKEN": ""}` | Scrubbed subprocess env so API-key fallback is structurally impossible |
| **Reasoning / budget** | | | |
| `effort` | Literal | **`"xhigh"`** (both predictor + learner) | Anthropic-recommended for long-horizon agentic reasoning |
| `thinking` | dict | `{"type": "adaptive"}` | Opus 4.7 requires adaptive (rejects `enabled` with budget_tokens) |
| `max_thinking_tokens` | int | not set | Superseded by `thinking`; `thinking` takes precedence |
| `max_turns` | int | predictor=20, learner=50 | Learner has harder work (spawns Data SubAgents); predictor is read-bundle-write-result |
| `max_budget_usd` | float | not set | Billed via OAuth subscription (not USD-metered) |
| `betas` | list | not set | Opus 4.7 has 1M context by default; no beta header needed |
| **Permissions & tools** | | | |
| `permission_mode` | Literal | `"bypassPermissions"` | Automated pipeline; no interactive prompts |
| `tools`, `allowed_tools`, `disallowed_tools` | list | not set | Full tool set needed (Data SubAgents, Write, etc.). Skill prompt handles scoping. |
| `can_use_tool` | callable | not set | No per-call permission logic needed |
| `permission_prompt_tool_name` | str | not set | No interactive prompting |
| **Observability** | | | |
| `stderr` | callable | `_stderr_sink` (log.info) | **DO NOT REMOVE** — drains subprocess stderr pipe. Without this, chatty subprocess output fills the buffer and subprocess dies with opaque "exit code 1". |
| `debug_stderr` | Any | not set | Using `stderr` callback instead |
| `include_partial_messages` | bool | not set (default False) | Set to True in future if we want live streaming of thinking/tool calls |
| **Context & I/O** | | | |
| `setting_sources` | list | `["project"]` | Load project's `.claude/settings.json` (hooks, MCP servers) |
| `cwd` | str/Path | not set | Default = process cwd (repo root) |
| `add_dirs` | list | not set | Not needed for our invocation |
| `settings` | str | not set | Project settings loaded via `setting_sources` |
| `user` | str | not set | Not needed |
| **Advanced / unused** | | | |
| `system_prompt` | str | not set | Use the skill's default system prompt |
| `mcp_servers` | dict | not set | MCP servers loaded via project settings |
| `continue_conversation` | bool | not set (False) | Each invocation is fresh |
| `resume` | str | not set | Not resuming prior sessions |
| `fork_session` | bool | not set (False) | Each call is its own session |
| `hooks` | dict | not set | Hooks loaded via project `.claude/settings.json` |
| `agents` | dict | not set | Agents loaded from `.claude/agents/` via project settings |
| `plugins` | list | not set | Plugins loaded via project settings |
| `sandbox` | SandboxSettings | not set | No sandboxing needed |
| `output_format` | dict | not set | Free-form output; validation done by our own code |
| `extra_args` | dict | not set | Escape hatch; not needed currently |
| `max_buffer_size` | int | not set | Default OK for our output sizes |
| `enable_file_checkpointing` | bool | not set (False) | Not using checkpointing |

**Summary of what we actively control**: 10 of 34 options are set. The rest use SDK defaults because our project's `.claude/settings.json` handles MCP/hooks/agents, and we don't need streaming/sandboxing/checkpointing yet.

### Deep-dive: thinking vs effort (two distinct parameters)

These are often conflated but do **different** things:

**`thinking`** — controls WHETHER/HOW extended thinking runs:
- `{"type": "adaptive"}` ← our choice. Model decides when to think deeply. **Required for Opus 4.7** (4.7 rejects the older `enabled` variant).
- `{"type": "enabled", "budget_tokens": N}` — manual budget. **NOT ACCEPTED by Opus 4.7** (400 error). Works on 4.6.
- `{"type": "disabled"}` — no thinking. Wrong for our use case.

**`effort`** — controls DEPTH/COST of all tokens (reasoning AND output):
- `low` / `medium` / `high` (default) / **`xhigh`** / `max`
- `xhigh` ← our choice. Anthropic-recommended for "long-horizon agentic tasks" (our learner: 8+ min, Data SubAgent spawning, evidence chasing).
- `max` = "absolute maximum, no constraints" but docs: *"adds significant cost for relatively small quality gains."* Use only if evals show `xhigh` is insufficient.
- Note: SDK v0.1.44's Python Literal type lists only `['low','medium','high','max']` — `xhigh` is missing from the type annotation but accepted at runtime (empirically verified).

**Our combo**: `thinking={"type": "adaptive"}` + `effort="xhigh"` = Anthropic-optimal for Opus 4.7 agentic reasoning.

### Permission modes: `auto` is available — but we stay on `bypassPermissions` for now

CLI v2.1.112+ offers 6 modes: `default`, `acceptEdits`, `plan`, **`auto`**, `dontAsk`, `bypassPermissions`.

**`auto`** is the newer recommended default per Anthropic docs:
- Server-side safety classifier (not interactive prompts)
- **Works in `-p`/SDK non-interactive mode** (fixed since v2.1.88 era)
- Blocks genuinely dangerous operations (`curl | bash`, force push, exfiltration) while allowing normal pipeline ops (local file writes, Task spawning, MCP queries)
- Requires `autoMode.environment` config in `.claude/settings.json` describing trusted infrastructure for best results

**`bypassPermissions`** (current):
- No classifier, all tools allowed except writes to protected dirs (`.git`, `.claude`)
- Proven working across 5 AVGO quarters today
- Vulnerable to prompt injection (classifier not defending)

**Decision (2026-04-16)**: stay on `bypassPermissions` until we explicitly test `auto` on a full pipeline run. Switching mid-calibration is too risky — the classifier could block a Data SubAgent or Write call and we'd have to debug. Switch to `auto` as a follow-up after we've evaluated it on at least one full AVGO+MSFT sweep.

**To test `auto` later**:
1. Add `autoMode.environment` to `.claude/settings.json`:
   ```json
   {
     "autoMode": {
       "environment": [
         "Organization: EventMarketDB. Primary use: earnings analysis and stock-move attribution.",
         "Trusted infra: Neo4j on minisforum3, Redis queue, K8s cluster minisforum*",
         "Local writes to earnings-analysis/Companies/*/events/*/learning/result.json are routine."
       ]
     }
   }
   ```
2. Change `permission_mode="bypassPermissions"` → `permission_mode="auto"` in both SDK calls
3. Run one full `--predict --learn` quarter and confirm: (a) no classifier blocks, (b) learner still spawns Data SubAgents, (c) learning/result.json still writes cleanly
4. If clean, switch permanently. If blocked, review the classifier reason and either tune `autoMode.environment` or revert.

### History of SDK-option changes (for audit)

| Date | Change | Reason |
|------|--------|--------|
| 2026-04-16 | Added `stderr=_stderr_sink` to both | Without it, SDK surfaces opaque "exit code 1" on subprocess errors |
| 2026-04-16 | Added `cli_path=_sdk_cli_path()` (system CLI) | Bundled CLI v2.1.59 was outdated + routed billing to API |
| 2026-04-16 | Added `env={"ANTHROPIC_API_KEY": "", ...}` | Defense-in-depth against env leak into subprocess |
| 2026-04-16 | `model="claude-opus-4-6"` → `"claude-opus-4-7"` | 4.7 released today; newer CLI handles its stricter thinking API |
| 2026-04-16 | `thinking` explicit `{"type": "adaptive"}` on predictor | 4.7 requires adaptive; predictor had no thinking config before |
| 2026-04-16 | `effort="high"` (learner only) → `effort="xhigh"` (both) | Docs recommend xhigh for long-horizon agentic reasoning |
| 2026-04-16 | `_assert_claude_code_oauth_ready()` guard before SDK calls | Fail-closed if API-only auth detected |
| 2026-04-16 | `ANTHROPIC_API_KEY` removed from `.env` | Root cause: dotenv was auto-injecting into subprocess |

### Critical: use SYSTEM claude CLI via `cli_path`, NOT the bundled one (2026-04-16)

**This is a billing + compatibility issue. Must not regress.**

`claude_agent_sdk==0.1.44` ships a BUNDLED `claude` binary at `venv/lib/python3.11/site-packages/claude_agent_sdk/_bundled/claude`. That bundled CLI is **v2.1.59** — months old. The user's system CLI (at `~/.local/bin/claude`) is v2.1.112 or newer.

**Two separate problems caused by using the old bundled CLI**:

1. **BILLING**: The old v2.1.59 bundled CLI does not correctly use the current OAuth subscription token format from `~/.claude/.credentials.json` (`claudeAiOauth`). Result: calls billed to ANTHROPIC API, not the Claude subscription. **User saw real API charges on 2026-04-16.**
2. **OPUS 4.7 COMPATIBILITY**: The old v2.1.59 CLI sends `thinking.type.enabled` + `budget_tokens` for internal tool-use / subagent API calls. Opus 4.7 rejects this — only accepts `thinking.type.adaptive`. Result: subprocess crashes with opaque "exit code 1" (real error only visible with `stderr=` callback: `API Error 400: "thinking.type.enabled" is not supported for this model. Use "thinking.type.adaptive"`).

**Fix (applied 2026-04-16)**: Pass `cli_path=shutil.which("claude")` to both `_run_predictor_via_sdk()` and `_run_learner_via_sdk()` so the SDK uses the system CLI. A module-level helper `_sdk_cli_path()` returns the system CLI path (or `None`, which falls back to bundled). See `earnings_orchestrator.py` constants near `PREDICTOR_MODEL_ID`.

**DO NOT**:
- Remove `cli_path=_sdk_cli_path()` from SDK calls without replacing it with a newer bundled CLI — doing so will silently revert to API billing.
- Remove `stderr=_stderr_sink` callbacks — without them, any future CLI issue will be opaque "exit code 1" instead of a real error.

**When upgrading `claude_agent_sdk` in the future**:
1. Check the new bundled CLI version: `ls venv/lib/python3.11/site-packages/claude_agent_sdk/_bundled/` and inspect its `--version` output
2. If bundled CLI is newer than system CLI, consider dropping `cli_path=` (the bundled will be fine)
3. **But** verify subscription billing either way by running a test quarter and checking the Anthropic console — do NOT assume
4. Test Opus 4.7 compatibility with a direct SDK test before enabling in production

**Environment audit baseline (for comparison on future debugging)**:
- `ANTHROPIC_API_KEY` env var: NOT SET (good — presence would force API billing)
- `~/.claude/.credentials.json`: contains `claudeAiOauth` (OAuth subscription token)
- `~/.claude.json`: `hasAvailableSubscription`, `oauthAccount` present (user is on subscription plan)

**How to diagnose "am I being billed API?"**: Run any SDK call with `stderr=print_lambda` capture, then check Anthropic API console (console.anthropic.com) for usage spikes. If console shows usage, API billing is happening. Subscription billing doesn't appear there.

### Historical: Opus 4.7 thinking-config compatibility — RESOLVED 2026-04-17

**Encountered 2026-04-16 (Opus 4.7 release day).** First attempt to run 4.7 failed with opaque "exit code 1" subprocess crashes.

**Real error** (only surfaces with `stderr=` callback on `ClaudeAgentOptions`):
```
API Error 400: "thinking.type.enabled" is not supported for this model.
Use "thinking.type.adaptive"
```

**Root cause**: `claude_agent_sdk==0.1.44` bundled Claude CLI v2.1.59, which predated 4.7 and internally generated `thinking.type.enabled` + `budget_tokens` for tool-use / subagent API calls. 4.7 rejects that shape (only accepts `adaptive`). 4.6 accepted both, which masked the issue initially.

**Temporary workaround (2026-04-16)**: `cli_path=_sdk_cli_path()` pointed the SDK at the system CLI (v2.1.112). Production briefly reverted to `claude-opus-4-6` to avoid blocking. See `CLAUDE.md` for the billing motivation that made `cli_path=` a permanent keep.

**Permanent fix (2026-04-17)**: Upgraded `claude-agent-sdk==0.1.44 → 0.1.61`. New SDK bundles CLI **v2.1.112** — same as the system CLI — which speaks 4.7 API natively. Production flipped back to Opus 4.7 + `effort=xhigh`. `cli_path=` kept in `ClaudeAgentOptions` as redundant-but-harmless (both bundled and system CLI are now v2.1.112) and to preserve subscription billing if someone ever downgrades the SDK.

**Durable lessons**:
- **Always pass `stderr=<callback>` to `ClaudeAgentOptions`.** Without it, SDK/CLI issues surface only as opaque "exit code 1". With it, you see real API errors. Both `_run_predictor_via_sdk()` and `_run_learner_via_sdk()` now carry `stderr=_stderr_sink`. Do NOT remove.
- **SDK upgrade is the preferred fix for CLI/API version skew** — not the `cli_path=<system>` workaround. Workaround was only used while `claude-agent-sdk==0.1.45+` was not yet released. Prefer `pip install --upgrade claude-agent-sdk` first.
- **When upgrading `claude-agent-sdk` in the future**: inspect `venv/lib/python3.11/site-packages/claude_agent_sdk/_cli_version.py` for the bundled CLI version. If bundled ≥ system CLI, `cli_path=` becomes strictly optional.

**Alternate workarounds considered but NOT shipped** (documented for completeness):
- Downgrade `thinking` to `None` — loses reasoning depth, never acceptable for this pipeline
- Explicit `betas=[...]` flag — not needed once the bundled CLI was current
- Patch the bundled CLI in place — brittle, defeats upgradability

This is operationally similar to the predictor SDK path but NOT the same runtime path. The predictor uses `"Run /earnings-prediction ..."` which triggers a Skill tool fork (14 tools, sufficient for read-bundle-write-result). The learner embeds SKILL.md content directly as prompt text, staying in the main session with full tools (27 built-in + MCP), enabling Agent tool access for all 14 Data SubAgents.

### Critical caveat: frontmatter is documentation, not runtime enforcement

Because the SKILL.md content is embedded as prompt text (not invoked via Skill tool), **frontmatter fields are not processed at runtime**:

| Frontmatter field | Runtime effect | Replacement |
|---|---|---|
| `model: opus` | None | `ClaudeAgentOptions(model="claude-opus-4-6")` — full model ID required, not short alias |
| `effort: high` | None | `ClaudeAgentOptions(effort="high", thinking={"type": "adaptive"})` + "ultrathink" in prompt body |
| `context: fork` | None (runs as main session) | This is the desired behavior |
| `allowed-tools` | None | Main session has all tools; no restriction needed |
| `skills:` | Not auto-loaded | Data SubAgents load their own skills when spawned |
| Skill-scoped hooks | Don't fire | Global hooks (pit_gate.py, PreToolUse Write validation) fire normally |

The SKILL.md frontmatter serves as **documentation of intent** (model, effort level, tools needed) even though Python SDK options are the actual enforcement mechanism. Global hooks in `settings.json` remain the validation boundary.

### Data SubAgent access from main session

The learner spawns Data SubAgents via Agent tool in the main session. Each agent (`.claude/agents/*.md`) loads its own skills, hooks, and PIT infrastructure. No wrapper skills or agent modifications needed — the existing 14 agents work as-is:

- 6 Neo4j agents: `neo4j-report`, `neo4j-transcript`, `neo4j-xbrl`, `neo4j-news`, `neo4j-entity`, `neo4j-vector-search`
- 3 external API agents: `alphavantage-earnings`, `yahoo-earnings`, `bz-news-api`
- 5 Perplexity agents: `perplexity-ask`, `perplexity-search`, `perplexity-reason`, `perplexity-research`, `perplexity-sec`

### Dev testing note

SDK sessions cannot nest inside Claude Code sessions (`CLAUDECODE` env var check). Production runs from cron/daemon/terminal (no issue). For dev testing from within Claude Code: `! unset CLAUDECODE && python3 scripts/run_learner.py AAPL Q1_FY2025`

### Write ownership model

The learner writes **only** `learning/result.json`. The orchestrator Python handles all derived writes:

1. **Learner** writes `learning/result.json` (validated by PreToolUse Write hook before disk write)
2. **Python** reads result.json after learner returns → validates schema
3. **Python** extracts `feedback` block + metadata → atomic append to `learnings/ticker/{TICKER}.json`
4. **Python** extracts `global_observations[]` → atomic append to `learnings/global.json`

This separation ensures: atomic file operations, safe concurrent ticker processing (global.json), simpler learner prompt (no file I/O instructions), and keeps the Skill vs Agent decision independent of file management.

**Completion semantics (happy path)**: When the learner produces valid output, a quarter is learner-complete only after: (1) `learning/result.json` is validated, AND (2) ticker.json append succeeds, AND (3) global.json append succeeds. The next quarter's prediction must not proceed until all three are confirmed — otherwise lessons are "written" but not actually available. If a derived write fails (e.g., ticker.json append), retry the append (not the full learner) — the valid result.json is the source of truth.

**Completion semantics (failure path)**: If the learner itself fails (no valid result.json after one retry), the historical failure policy in §2 applies: the ticker's sequential processing stops at this quarter. The failure is logged. Re-bootstrap after investigation.

**Atomic append pattern**: `fcntl.flock()` exclusive lock + write to temp file + `os.replace()`. Required for `global.json` (concurrent ticker processing). Recommended for `ticker.json` (crash safety, no concurrency risk for single-ticker sequential processing).

### Validation strategy regardless of choice

**Layer 3 — PreToolUse Write hook** (works for both Skill and Agent):
Validates `learning/result.json` JSON before disk write. Checks:
- JSON parseable
- All required fields present
- `feedback` block has all 6 sub-fields
- Array caps respected (what_worked ≤ 2, what_failed ≤ 3, predictor_lessons ≤ 3, data_lessons ≤ 3)
- `missing_inputs` is an array
- `evidence_ledger` is non-empty and all driver `evidence_refs` resolve to ledger IDs
- `global_observations` array present (may be empty)

**Post-return validation** (orchestrator Python):
After learner returns, orchestrator checks:
- `learning/result.json` exists at expected path
- JSON valid and schema matches
- If validation fails: log warning, re-invoke with corrective prompt (max 1 retry). If still invalid, stop ticker's bootstrap per §2 historical failure policy

### Max turns guardrail

Set `max_turns: 50` as a guardrail. This is a safety cap, not a target. The learner should use as many turns as needed (typically 15-30) and stop when confident, well before the cap.

---

## 11. What to Reuse from Old Attribution Skill

**Borrow (reasoning quality)**:
- Evidence-based methodology: every claim must cite source → retained as `evidence_ledger` with ID refs
- Data inventory first: know what data exists before making claims → retained as investigation step 1
- Source priority hierarchy: primary filings > transcript > official news > analyst coverage > general news → guidance for causal weight
- Conflict resolution: note conflicts explicitly rather than silently choosing → retained as principle
- Neo4j subagent spawning patterns: parallel fetch, PIT-aware, resume for follow-up → retained

**Discard (stale contract)**:
- Markdown report output → replaced by JSON-first `learning/result.json`
- `subagent-history.csv` tracking → no longer needed
- `predictions.csv` / `8k_fact_universe.csv` tracking → no longer needed
- Step 10 (mark completed in CSV) → orchestrator handles completion tracking
- Step 11 (Obsidian thinking index build) → out of scope
- `learnings.md` per-company file → replaced by `learnings/ticker/{TICKER}.json`
- Pattern-matching categories (Beat-and-Raise, etc.) → derived from evidence, not pre-defined
- Surprise calculation formulas → predictor already handles; learner does causal attribution
- Human-readable confidence assessment section → replaced by `feedback.why` + lesson quality

---

## 12. Dependencies (NOT in learner scope)

These must exist for the learner to function but are built elsewhere:

| Dependency | Owner | Status |
|------------|-------|--------|
| Sequential quarter processing (Q(n) before Q(n+1)) | Orchestrator SKILL.md / earnings_orchestrator.py | **Not implemented** — orchestrator handles one quarter via CLI |
| `is_historical_done()` deferred learner check | Trigger daemon (EarningsTrigger.md) | **Not implemented** — pseudocode only. Note: daemon must distinguish "daily_stock not settled yet" (learner ineligible) from "daily_stock exists, learner eligible but missing" (enqueue historical) to avoid pointless re-enqueues |
| Guidance gate for historical bootstrap | Trigger daemon | **Not implemented** — pseudocode only |
| `get_quarterly_filings()` returning filed_8k timestamps | `scripts/get_quarterly_filings.py` | **Implemented** |
| PIT gate + fetch infrastructure | `pit_gate.py`, `pit_fetch.py` | **Implemented** |
| Neo4j Data SubAgents | `.claude/agents/neo4j-*.md` | **Implemented** |
| External API Data SubAgents | alphavantage, yahoo, bz-news-api agents | **Implemented** |
| prediction/result.json written by predictor | earnings-prediction skill | **Implemented** |
| PUBLISHED_AS return data on 8-K reports | Neo4j ingestion pipeline | **Implemented** |

---

## 13. Implementation Checklist

### Phase 1: Learner Contract

- [ ] Create `.claude/skills/earnings-learner/SKILL.md` — compact prompt with 5-phase workflow, evidence rules, generalizability guardrail. Frontmatter documents intent (`model: opus`, `effort: high`) but is not runtime enforcement (§10). **⚠️ HUMAN REVIEW GATE — every line must be approved before proceeding**
- [ ] Add `get_attribution_paths()` and learning-file path helpers in `earnings_orchestrator.py` (deterministic result locations from day one)
- [ ] Add `validate_attribution_result()` in Python — canonical schema check (required fields, feedback sub-fields, array caps, evidence_refs resolution, non-empty evidence_ledger). The PreToolUse hook mirrors this contract
- [ ] Create PreToolUse validation hook for `learning/result.json` writes (shell script calling the same checks)
- [ ] Create `_run_learner_via_sdk()` in `earnings_orchestrator.py` — loads SKILL.md content, strips frontmatter, embeds as prompt text with runtime inputs, invokes via SDK with `model="claude-opus-4-6"`, `effort="high"`, `thinking={"type": "adaptive"}`, `max_turns=50`

### Phase 2: Lesson Infrastructure

- [x] Create `earnings-analysis/learnings/` directory structure
- [x] Implement ticker.json atomic append in `earnings_orchestrator.py` (extract feedback, temp file + `os.replace` — no flock needed, single-ticker sequential)
- [x] Implement global.json atomic append in `earnings_orchestrator.py` (extract global_observations, enrich metadata, `fcntl.flock` + atomic write for concurrency safety)
- [x] Add `build_learning_context()` in `earnings_orchestrator.py` (lightweight file read, not in `builder_adapters.py` — no external deps). Per-scope caps, exact-text dedupe, quarter_label dedupe for rerun idempotency
- [x] Add `_render_learning_context()` in `earnings_orchestrator.py`
- [x] Wire `learning_context` as logical 8th bundle field in `build_prediction_bundle()` (post-build, not in `BUNDLE_ITEM_ORDER` which stays at 7 parallel builders)

### Phase 3: Orchestrator Inputs + Integration

- [x] Add `derive_learner_pit()`: three-tier PIT rule (next_quarter → live_cycle → invocation_time). Verified on 11 AAPL quarters. **⚠️ HUMAN REVIEW GATE — must verify correctness across all tickers**
- [x] Add `normalize_actual_return()` + `fetch_actual_return()`: Neo4j PUBLISHED_AS query + field name mapping to `_pct` suffix + daily_stock hard gate
- [x] Add `run_learner_for_quarter()`: full pipeline with hard gates, PIT derivation, existing-result recovery (derived-write recovery before Neo4j fetch), SDK invocation, post-return validation (1 retry), ticker+global lesson appends
- [x] Add `--learn` CLI flag to `main()` — single-quarter learner invocation (loads event.json for PIT derivation)
- [x] Update orchestrator SKILL.md invariants to reflect derived-write recovery behavior

### Pending (separate from Phase 3)

- [ ] Wire deferred learner detection in trigger daemon (`is_historical_done()` checks learning/result.json existence)

### Phase 4: Calibration — **⚠️ HUMAN REVIEW GATE**

Manual single-quarter runs via CLI: `python3 scripts/earnings/earnings_orchestrator.py TICKER ACCESSION --save --predict --learn`. Full sequential automation is pending (daemon, §12).

**Sequential execution is REQUIRED for calibration**: Quarters must run one-at-a-time in chronological order (Q1 → Q2 → Q3 → …). This is not optional — each quarter's learner writes lessons that the NEXT quarter's predictor reads via `learning_context`. Running in parallel or out of order breaks the U1 loop (Q(n) predictor would miss Q(n-1)'s lessons). For a batch run, shell-chain commands: `cmd1 && cmd2 && cmd3` (AND-chain so a failure stops the chain). Never `&` (background) or multi-terminal parallel runs.

**Progress (AVGO sequential calibration, 2026-04-16):**
- Q1_FY2023: learner-only (legacy prediction), schema-valid, primary_driver=`ai_narrative_rerating`, direction_correct=False. Uncovered real predictor data-freshness bug via investigation.
- Q2_FY2023: **first clean full-pipeline end-to-end success.** Bundle 7/7, predict+learn via SDK on Opus 4.7, predictor validation passed, learner validation passed, U1 loop verified (Q1 lesson flowed into Q2 bundle, Q2 direction_correct=True, magnitude_error=0.0 with actual inside predicted range).

### ⚠️ Empirical finding: template-overfit risk from lesson accumulation (2026-04-16)

**A/B baseline on AVGO Q1–Q5 showed zero net uplift** from lessons:
- WITH lessons: 3/5 direction-correct (60%)
- WITHOUT lessons: 3/5 direction-correct (60%)
- Delta: 0 on 5 quarters (statistically indistinguishable from LLM variance)

**The trade behind the zero net**:
- Lessons HELPED on Q2_FY2023 (+1): Q1's "AI narrative quantification as primary signal" lesson correctly steered the predictor to long.
- Lessons HURT on Q3_FY2023 (−1): the AI-narrative template that worked for Q2 became a bias that overrode the bundle's non-AI segment weakness signal. Predictor stayed long when the actual signal was a segment inflection.
- Neutral on Q1 (both wrong, no prior context either way), Q4, Q1_FY2024 (both right — the bundle signal was strong enough without lesson help).

**Risk name: "template overfit"**. Once a pattern is in the lesson bank AND matched to the current quarter's bundle, the predictor may over-commit to the template even when fundamental evidence contradicts. The learner's own Q3 attribution recognized this post-hoc ("default to FLAT or SHORT on thin beat + rallied-into-print") — but that lesson came too late to rescue Q3 itself; it benefits Q4+.

**What this implies for the design**:
1. **Lessons are not free alpha.** At this sample size they appear breakeven; at larger samples they might help or hurt. No claim of uplift is warranted yet.
2. **Template matching can become a crutch.** The predictor should treat lessons as *soft priors*, not *hard rules* — if bundle evidence contradicts a lesson, the bundle evidence must win. Today's SKILL.md already says "soft priors" but the empirical behavior in Q3 shows the LLM can still over-weight template fits.
3. **The fix is NOT more guardrails in the SKILL.md prompt** — prompting an LLM harder to "ignore the lesson" creates an unstable incentive. The right fix is to **accumulate enough lessons that contradictions across them force the predictor to weigh bundle evidence directly**, and to keep lessons compact and non-dominant in the prompt budget.
4. **Monitoring needed**: track the "same direction as most recent lesson" rate vs hit rate over time. If the predictor just parrots the most recent lesson regardless of bundle, that's the overfit failure mode.
5. **No new code change today.** This is an observation for calibration monitoring, not an architectural red flag. Real evaluation needs ≥30 quarters across ≥5 tickers and sectors, with A/B on each.

**What NOT to conclude**:
- "Lessons don't work" — n=5 is not enough data.
- "Lessons are harmful" — the one hurt case has a natural explanation (first time a multi-quarter template failed), and the Q3 learner corrected itself.
- "We should remove the learner" — the infrastructure value (audit trail, evidence, U1 feedback) is independent of current predictor uplift.

**Raw A/B data**: `earnings-analysis/test-outputs/ab_baseline_AVGO.json`

### Proposed mitigation for template overfit — "labeled lesson consumption"

**Do NOT apply this yet.** This is the designed fix IF a second ticker (NVDA, AAPL, ...) shows recurring Q3-style overfit. Documented here so future bots know the exact intervention and can implement it directly, not re-derive.

**What it does**: Before the predictor uses any prior lesson in its final call, it must explicitly label each lesson as `confirmed`, `contradicted`, or `irrelevant` based on whether the CURRENT-quarter bundle independently shows the lesson's mechanism. Only `confirmed` lessons may influence the directional call.

**Why this is better than the other considered fixes**:

| Option considered | Why rejected (at time of writing) |
|---|---|
| Drop success-quarter lessons (keep only wrong-quarter) | Crude — loses genuine positive signal like Q2's "differentiate narrative-fading vs narrative-priced-in" |
| Strip `predictor_lessons` + `why` + `category` from render | Amputates U1 loop — learner becomes a pure error ledger with no forward guidance |
| Add SKILL.md hard rule "ignore lesson if bundle doesn't show mechanism" | LLMs are poor at following soft meta-rules in prose. SKILL.md already says "soft priors" and Q3 overfit happened anyway. |
| **Labeled lesson consumption (THIS)** | Structured metacognitive step — LLMs handle classify tasks better than soft rules. Produces audit trail. Keeps all lessons intact. |

**Mechanism trace (why it would have caught Q3)**:
- Lesson from Q1 (AVGO): *"When company first quantifies AI revenue, treat as narrative re-rating signal."*
- Q3 bundle (independent check): does Q3 show FIRST quantification? No — AI already quantified in Q1 and Q2.
- Label: `irrelevant` (mechanism not present)
- Predictor doesn't apply → weighs bundle evidence → may catch non-AI segment weakness
- Instead of silently pattern-matching "AI lesson + some AI in bundle → apply"

**Honest limitations — this is not a silver bullet**:
1. **Confirmation bias**: the same LLM that wants to apply a lesson also decides if it applies. May label `confirmed` too liberally.
2. **Label noise**: LLMs misclassify. Some fraction of `irrelevant` lessons will be mislabeled `confirmed`. Overfit reduced, not eliminated.
3. **Cost**: adds ~20-30% to predictor token usage (labeling step) and ~30s latency per prediction.
4. **Estimated impact**: honest guess is 50-70% reduction in Q3-style overfit failures if labels are reasonable. Not 100%.

**Implementation requirements (when the time comes)**:

1. **Predictor SKILL.md changes** (`.claude/skills/earnings-prediction/SKILL.md`):
   - Add new Phase between "Load Context" and "Analyze": **"Label Prior Lessons."**
   - For each lesson in `ticker_lessons[]` and `global_lessons[]` received via `learning_context`, the predictor emits a label `{lesson_id, label, bundle_evidence}` where:
     - `label`: `"confirmed"` / `"contradicted"` / `"irrelevant"`
     - `bundle_evidence`: 1-sentence citation of what in the current bundle supports the label (or "no relevant evidence")
   - Hard rule: **only `confirmed` lessons may be cited as reasoning in the final call.** `contradicted` and `irrelevant` lessons must be ignored for directional decisions.

2. **`prediction_result.v1` schema extension — STRUCTURED, not prose**:
   - Add top-level field `lesson_labels: [{quarter_label, lesson_text_or_id, label, bundle_evidence}]`
   - `quarter_label`: the source quarter of the lesson (so auditors know which prior quarter's advice is being labeled — e.g., `"Q3_FY2023"`)
   - `lesson_text_or_id`: the actual lesson string OR a stable identifier that maps back to the lesson text
   - `label`: **strictly one of** `"confirmed"`, `"contradicted"`, `"irrelevant"` — no synonyms, no freeform values
   - `bundle_evidence`: 1-sentence citation from the current-quarter bundle that supports the label (or `"no relevant evidence"` for `irrelevant`)
   - One entry per lesson consumed from `learning_context.ticker_lessons[]` and `learning_context.global_lessons[]`
   - **Rationale**: the fix's value is not JUST better reasoning — it's that we can INSPECT whether the model is labeling honestly or rubber-stamping everything as `confirmed`. Prose-hidden labels are un-auditable.
   - Validator enforces the enum on `label` field

3. **Python-side changes**:
   - `finalize_prediction_result()` preserves `lesson_labels` if the LLM wrote it
   - `validate_prediction_result()` — optional: validate label values are in the allowed enum
   - New `audit_lesson_labels()` utility (offline) that samples labels across quarters and reports `confirmed` rate — if it's >80%, classifier is biased and we need harder intervention

4. **Learner unchanged**: the learner keeps producing lessons the same way. Only the PREDICTOR's consumption changes. This is a one-sided change.

5. **A/B test plan once implemented**:
   - Re-run 10+ quarters across 2+ tickers with the labeled-consumption predictor
   - Compare to existing no-label results on same bundles
   - Audit 20+ lesson labels manually for honesty
   - If `confirmed`-rate is sensibly distributed (e.g., 30-60% labeled `confirmed`) AND hit rate improves OR overfit cases reduce, mitigation works
   - If `confirmed`-rate is >80% (label-everything-confirmed), approach is compromised — need a separate classifier LLM run

**Alternative if labels are dishonest (confirmation bias too strong)**: instead of the predictor labeling its own lessons, use a separate SDK call to a LABEL-ONLY LLM that sees only `(lesson, bundle)` pairs and returns labels. That LLM has no stake in the prediction, no confirmation bias. More expensive but more honest.

#### Verified-claims review (independent read of ChatGPT's minimal-footprint proposal, 2026-04-16)

ChatGPT argued the mitigation can land as a "minimal-footprint" change — no predictor architecture rewrite, no learner changes, purely additive to `prediction_result.v1`. Independent verification of that claim:

| Claim | Verified? | Notes |
|---|---|---|
| Learner is unchanged | ✅ Correct | The mitigation is entirely on the predictor's consumption side. `attribution_result.v2`, `ticker_lessons.v1`, `global_lessons.v1` all untouched. `build_learning_context()` is unchanged. |
| `prediction_result.v1` gains one additive field | ✅ Correct | `lesson_labels: []` is strictly additive. Existing consumers (A/B scripts, `finalize_prediction_result()`, validator) ignore unknown fields. Backward-compatible. |
| Predictor changes are SKILL.md-only (no Python) | ✅ Mostly correct | One new phase in SKILL.md ("Label Prior Lessons") + a rule ("only confirmed may influence direction"). **But** validator should gain an enum check on `label` (small addition to `validate_prediction_result()` or a new sibling validator). Without it, prose labels leak in. |
| Cost is bounded (~20-30% token uplift) | ✅ Plausible | Labels are short per-lesson JSON blobs. Worst case with 15 ticker + 10 global lessons = 25 entries × ~40 tokens each ≈ 1000 tokens output. Predictor call already runs ~8-12k tokens output, so ~10% uplift, not 30%. I had overestimated earlier. |
| Audit is possible by reading prediction JSONs only | ✅ Correct | All label decisions live in `prediction_result.v1.lesson_labels`. Offline audit script reads N predictions, aggregates `confirmed`-rate per ticker/per lesson, flags rubber-stamping. No state needed anywhere else. |

**Conclusion**: the minimal-footprint framing holds. No architectural objection to shipping this as designed. The 5 refinements below tighten edge cases before implementation.

#### Five refinements before implementation

These are the gaps in the original sketch — each is small and each prevents a known failure mode.

1. **SKILL.md must ship a concrete EXAMPLE block with filled `lesson_labels`.** LLMs are dramatically more consistent when the prompt demonstrates the schema. Example to embed verbatim:

   ```json
   "lesson_labels": [
     {
       "quarter_label": "Q1_FY2023",
       "lesson_text_or_id": "When company first quantifies AI revenue, treat as narrative re-rating signal.",
       "label": "irrelevant",
       "bundle_evidence": "Current bundle shows AI revenue was already quantified in prior two quarters; no new quantification disclosed."
     },
     {
       "quarter_label": "Q2_FY2023",
       "lesson_text_or_id": "Thin beat + rally-into-print → favor short/flat.",
       "label": "confirmed",
       "bundle_evidence": "Pre-print 5-day return was +7.2% and revenue beat consensus by only 0.4%."
     },
     {
       "quarter_label": "global:2024-05-03",
       "lesson_text_or_id": "Semis with >50% hyperscaler concentration → treat guidance raise as priced-in.",
       "label": "contradicted",
       "bundle_evidence": "Company flagged new non-hyperscaler customer wins in prepared remarks — concentration thesis weakens."
     }
   ]
   ```

2. **Explicit empty-case rule.** When `learning_context.ticker_lessons` and `global_lessons` are both empty (first quarter of a ticker, no global lessons yet), the predictor **must emit `"lesson_labels": []`**, not omit the field and not fabricate entries. Validator requires the field to be present even when empty.

3. **Validator edge cases — be exact.** `validate_prediction_result()` must handle four degenerate cases, each deterministically:
   - **Missing key** (`lesson_labels` field absent): treat as `[]`, do NOT block. Old predictions predate the field.
   - **`null` value**: block. Ambiguous — likely LLM confusion.
   - **Invalid enum** on `label` (e.g. `"maybe"`, `"partial"`, `"CONFIRMED"`): block. Enum is strictly `confirmed|contradicted|irrelevant` lowercase.
   - **Empty `bundle_evidence` string** on a `confirmed` label: block. Cannot claim confirmation with no evidence. (For `irrelevant`, allow `"no relevant evidence"` as the literal string.)

4. **Audit threshold: >70%, not >80%.** Original sketch said flag rubber-stamping if `confirmed`-rate >80%. Tighten to **>70%**, because:
   - In a balanced lesson bank, priors suggest 30-50% of lessons should match a given quarter's mechanism (most lessons are ticker/scenario-specific).
   - >70% `confirmed` across ≥10 quarters is statistically strong evidence of label bias, not a hard-to-achieve threshold that lets bias hide.
   - The offline audit script emits a WARNING at >70% and a HARD FLAG at >85%.

5. **Plan doc update (meta).** When this mitigation goes live, the following sections of `learner.md` also need amendment:
   - **§10 SDK options inventory**: add `lesson_labels` to the predictor output contract listing.
   - **Phase 4 checklist** (appended to this section): new bullet "verify `lesson_labels[]` is emitted, enum-valid, and non-empty when lessons exist."
   - **Known Issues**: retire the "template overfit observed, no fix active" note; replace with "template overfit mitigated via labeled lesson consumption — audit `confirmed`-rate monthly."

**What is explicitly NOT needed** (rejected additions to the design):
- A separate classifier LLM as the default (reserve for the `>85%` rubber-stamp failure mode only).
- Learner-side changes (the learner doesn't need to know lessons are being labeled downstream).
- New Python module files (additions fit inside existing `earnings_orchestrator.py` + `validate_attribution.py`).
- Schema version bump for `prediction_result.v1` (additive fields don't require a version bump).

**Estimated implementation effort**: ~100-150 lines across SKILL.md (example + phase + rule), validator (enum + edge cases), and one new offline audit script. No subprocess/auth/SDK work.

- [ ] Run learner on 3-5 historical quarters for one ticker
- [ ] Verify lesson quality — learner uses full evidence surface and produces reusable high-signal guidance, not quarter-specific summaries
- [ ] Verify PIT enforcement (no post-boundary evidence in historical runs)
- [ ] Verify `build_learning_context()` produces useful predictor context
- [ ] Run predictor WITH lessons vs WITHOUT — compare prediction quality

---

## Appendix: Canonical Filing Structure

```
earnings-analysis/
  Companies/
    AAPL/
      events/
        event.json                          ← rebuilt by get_quarterly_filings
        Q1_FY2025/
          prediction/
            context_bundle.json             ← predictor input bundle
            result.json                     ← predictor output
          learning/                         ← renamed from attribution/ per obsidian_thinking.md 2026-04-17
            result.json                     ← LEARNER OUTPUT (this plan)
        Q2_FY2025/
          ...
  learnings/
    ticker/
      AAPL.json                             ← TICKER LESSONS (this plan)
      MSFT.json
    global.json                             ← GLOBAL LESSONS (this plan)
```
