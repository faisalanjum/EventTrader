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

Canonical actionable backlog for the learner subsystem. Supersedes the backlog lists in `Appendix A` §10 and §12 (those sections now cross-reference here). Items grouped by priority; detailed designs and rejected-alternatives remain in `Appendix A`.

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
- The `Appendix A` schema-structured-routing fix from 2026-04-17 — T1.5 is strictly additive to that work.

> ⚠ Explicit non-invariant: the bundle-PIT default in T1.5a DOES change behavior for manual CLI callers that invoke `--predict`/`--learn` on historical accessions without `--pit`. This is intentional — the old behavior is the root cause of the corpus PIT poisoning. Callers that intentionally want live-mode against a historical accession must now pass `--live`. See "Behavior changes by caller type" in Corpus implications above.

---

### 🔴 Next up — highest EV, **blocked on T1.5 shipping + corpus re-run**

| # | Item | Summary | Where to start |
|---|---|---|---|
| T1 | **Template-overfit mitigation — "labeled lesson consumption"** | ✅ **IMPLEMENTED 2026-04-19** — structural enforcement via validator (positional equality + `cites_lesson_indices` confirmed-only + `bundle_evidence` sentinel discipline + `analysis` substring floor). Authoritative spec: ``.claude/plans/learner.md` Appendix B` (rev 3.6). Phase 0 added to predictor SKILL.md; `validate_prediction_result` extended; all 6 call sites wired with `expected_lesson_texts=` kwarg. | SHIPPED — see Appendix B §§7-8 for full implementation. Offline audit script deferred to separate PR after ≥10 T1 quarters exist. |
| T2 | **Populate `guidance_history.series`** — structured guidance extraction | 100% of calibration quarters currently have `series = []`; predictor is inferring guide-vs-consensus from press-release prose. Plausibly higher EV than any lesson-routing change: lessons cannot compensate for missing structured fields. | New builder or enrichment on top of existing guidance pipeline. Trace `build_guidance_history` flow; populate `series` from XBRL/transcript/8-K fields. |
| T3 | **Fix `builder_adapters.build_8k_packet` to populate `sector` at source** | Legacy builder returns `sector=None` on 100% of bundles, making `_lookup_company_sector` fallback in `build_prediction_bundle` load-bearing rather than defensive. | Trace delegation to `warmup_cache.build_8k_packet` and add sector-stamping. When fixed, `_lookup_company_sector` becomes truly optional and can be scoped to the write-side `source_sector` stamp only. |

### 🟡 Backlog — tracked, post-re-run or opportunistic

| # | Item | Summary | Where to start |
|---|---|---|---|
| T4 | **Fresh WITH-vs-WITHOUT A/B evaluation** after the full 15-quarter re-run | Two confounds block an honest measurement today: (1) BURL A/B used Opus 4.6/high vs AVGO/NVDA on 4.7/xhigh, and (2) **the entire existing corpus is PIT-poisoned** — every prediction was made with 2026 peer/macro/guidance data against 2023–2024 events (see T1.5 above). A/B can only produce honest signal after **T1.5a+b ship → corpus wipe → full 15-quarter re-run completes with PIT-safe defaults**. Required before any claim that "the learner helps prediction." | `scripts/run_avgo_ab_sequential.py` / `run_nvda_ab_sequential.py` / `run_burl_ab_sequential.py` against the new post-wipe, post-T1.5 data. |
| T5 | **obsidian_thinking.md ship coordination** | When that plan lands, it renames `validate_attribution.py` → `validate_learning.py`, `validate_attribution_output.py` → `validate_learning_output.py`, `attribution/` dir → `learning/`, `finalize_attribution_result` → `finalize_learning_result`, etc. | Mechanical ~15-min `sed`-style pass against the rename table in `Appendix A` §0. No logical conflict — learner-edits ships first. |
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

### 🗑️ Declined — documented in `Appendix A` Appendix C

For the record (not actionable): same-sector fallback for cross_ticker routing, dual-read migration mode, concrete worked examples in SKILL.md, keeping `scope_key` as vestigial display field, schema version bump for `global_lessons.v1`→v2. See `Appendix A` Appendix C for the full rationale per rejected alternative.

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
  // placeholder `lesson` text per Appendix A §6.7 — do not copy.

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
| `global_observations` | Yes | Array (max 3), scope-conditional shape per ``.claude/plans/learner.md` Appendix A` §4.1: `{scope:"sector", target_sector, lesson}` / `{scope:"macro", lesson}` / `{scope:"cross_ticker", related_tickers, lesson}`. `scope_key` REMOVED (amendment 2026-04-17 — validator rejects). Can be `[]`. Python upserts these into `global.json` by `(source_ticker, quarter_label)`. |
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

> **AMENDED 2026-04-17** — the schema below reflects the **structured-routing** contract from ``.claude/plans/learner.md` Appendix A`. `scope_key` has been removed; routing is by `target_sector` (sector scope) or `related_tickers` (cross_ticker scope). See `Appendix A` §4 for the full authoritative schema and §6.2 for the writer semantics.

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

**T1.5b storage-metadata fields (2026-04-17)** — `source_filed_8k` and `source_pit_cutoff` are Python-stamped on every new entry (both scopes), copied verbatim from the `filed_8k` + `pit_cutoff` top-level fields on `attribution_result.v2`. They are NOT learner-output contract fields and are NOT validated by `validate_attribution.py`. The read-side PIT filter in `build_learning_context` uses `source_pit_cutoff` (with tz-aware chronological comparison) to exclude lessons whose source event's pit_cutoff is after the predictor's pit_cutoff. Legacy entries missing these fields are excluded in historical mode and passed through in live mode (preserving pre-T1.5b production behavior).

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

> **AMENDED 2026-04-17** — routing is now structured-field based (no regex, no `scope_key` matching). See ``.claude/plans/learner.md` Appendix A` §4.3 and §6.3 for the authoritative filter logic and observability contract. The `sector_lookup` callable parameter has been removed from the signature.

**Location**: `scripts/earnings/earnings_orchestrator.py` (not `builder_adapters.py` — this is a lightweight local file read; bundle-level current-ticker sector resolution uses the Neo4j-backed `_lookup_company_sector` fallback when `8k_packet.sector` is None, which is the common case).
**Role**: Read-time compatibility layer that transforms derived lesson files into predictor-ready compact context. Emits one structured-counter log line per call.

### Interface

```python
def build_learning_context(ticker: str, sector: str | None = None,
                           base_dir: Path | None = None,
                           pit_cutoff: str | None = None) -> dict:
    """Build learning context for predictor consumption.

    Reads ticker lessons and global lessons, filters by recency and relevance,
    returns compact context suitable for inclusion in the prediction bundle.

    T1.5b (2026-04-17): pit_cutoff enables PIT filtering at read time.
    - None  → live mode: no filter applied (production real-time preserved).
    - ISO-8601 string → historical mode: entry visible iff
      `source_pit_cutoff <= pit_cutoff` via tz-aware datetime comparison.
      Entries missing `source_pit_cutoff` (legacy) → excluded; both naive
      and malformed timestamps → defensively excluded.
    Applies uniformly to ticker lessons and all four global scopes
    (ticker, sector, macro, cross_ticker).
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
- **No same-sector fallback** for cross_ticker — broad lessons belong in `scope=sector`. See `Appendix A` Appendix C "rejected alternatives" for the pollution rationale.
- Every exclusion increments a named counter. Six scope-routing counters (`sector_mismatch`, `current_sector_unknown`, `cross_ticker_not_listed`, `cross_ticker_missing_related`, `unknown_scope`, `legacy_schema`) plus two T1.5b PIT-filter counters (`ticker_post_cutoff`, `global_post_cutoff`) — the latter fires BEFORE scope routing for any entry whose `source_pit_cutoff` is after the predictor's `pit_cutoff`, so PIT exclusions are disjoint from scope exclusions. An observability log line fires on every call — even when `global.json` is absent.
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

> **STATUS**: ✅ SHIPPED 2026-04-19. Authoritative spec: ``.claude/plans/learner.md` Appendix B` (rev 3.6). The design sketch below is retained for historical context only — ALL references to "future", "propose", "when the time comes", etc., are obsolete. Refer to the consumption plan file for the implemented contract.


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


---

# Appendix A — Structured Routing Permanent Fix (formerly `learner-edits.md`)

> **Status**: SHIPPED. Merged into this file on 2026-04-19 (was `.claude/plans/learner-edits.md`).
> Section numbering below is SELF-CONTAINED to this appendix — do not confuse with learner.md §N.


**Created**: 2026-04-17
**Status**: APPROVED — ready for single atomic-commit implementation
**Scope**: Replace the current `cross_ticker` stopgap (regex-based scope_key parsing + Neo4j-in-reader fallback) with a structured-schema permanent fix. Also fix the parallel silent-drop bug in the `sector` scope filter, and eliminate the `scope_key` "double duty" (routing + display) by adding `target_sector` + `related_tickers` as structured routing fields.

**Supersedes in `.claude/plans/learner.md`**: §8 (global_observations schema), §9 (`build_learning_context` filtering logic). Everything else in `learner.md` remains authoritative.

**Does NOT change**: the learner's invocation pattern (§10), PIT gating (§3), predictor contract, or any other subsystem.

**Interaction with `obsidian_thinking.md` (independent plan)** — orthogonal data domains. This plan touches `earnings-analysis/learnings/` (aggregate lessons); obsidian_thinking touches per-quarter artifacts under `earnings-analysis/Companies/*/events/*/` (thinking capture + artifact layout).

**Confirmed ship-order: THIS plan ships FIRST.** Rationale: (a) our post-commit wipe + 15-quarter re-run is safer against a quiet events tree, (b) obsidian_thinking's baseline migration is cleaner against a known-good learner dataset, (c) no shared function edits and no logical conflict.

**If obsidian_thinking ever ships first instead**, this plan's path literals, file names, and Python identifiers all need a coordinated find-replace pass (pure rename, no logic change). Full rename table — keep this synchronized with `.claude/plans/obsidian_thinking.md` if that plan mutates:

| This plan currently references | Rename to (if obsidian_thinking landed first) |
|---|---|
| `attribution/result.json` (path under `events/{Q}/`) | `learning/result.json` |
| `attribution/` (the per-quarter directory name) | `learning/` |
| `scripts/earnings/validate_attribution.py` | `scripts/earnings/validate_learning.py` |
| `.claude/hooks/validate_attribution_output.py` | `.claude/hooks/validate_learning_output.py` |
| `get_attribution_paths()` / `get_attribution_dir()` | `get_learning_paths()` / `get_learning_dir()` |
| `finalize_attribution_result()` | `finalize_learning_result()` |
| `prediction/context_bundle.{json,txt}` | `context_bundle.{json,txt}` (promoted to quarter root) |
| `prediction/ab_baseline/result_NO_LESSONS.json` | `experiments/prediction_no_lessons/result.json` |

See obsidian_thinking.md file-inventory section (lines ~245–260) for the authoritative rename list and motivation. The renames are mechanical — no logic change to any function or schema — so a ~15-minute coordinated pass (`sed -i` across this plan + the matching source-code files) is all that's required if ship-order reverses.

**Schema version policy (implementer-facing)**: `schema_version` in `attribution/result.json` stays at `"attribution_result.v2"` — NO bump. Rationale: (a) §5.1 audit confirms zero external consumers of this schema outside the repo; (b) the change is additive for new scopes plus a single removal (`scope_key`), not a breaking restructure; (c) clean-slate wipe eliminates all pre-amendment stored data, so there is no "mixed-version" read window. The validator at `scripts/earnings/validate_attribution.py` continues to hard-check `payload["schema_version"] == "attribution_result.v2"`; do NOT change that string. If a future change is genuinely breaking (e.g., removes a required routing field or changes semantics of an existing one), bump to `v3` at that point, not now.

---

## 0. TL;DR

Two silent-drop bugs in `scripts/earnings/earnings_orchestrator.py::build_learning_context`:

1. **`cross_ticker` scope** — originally `pass`-dropped every entry unconditionally (before codex's stopgap). Learner wrote them faithfully; storage preserved them; reader discarded them.
2. **`sector` scope** — used raw string equality `scope_key == sector`, which the learner routinely breaks by writing non-canonical labels (`"semiconductors"`, `"off_price_retail"`) while Neo4j returns canonical labels (`Technology`, `ConsumerCyclical`). Silently broken too.

Additionally, **`8k_packet.sector = None` on all 15 calibration bundles** (verified), so `build_prediction_bundle` could not know the current ticker's sector without an external lookup.

**Fix** (single atomic commit): introduce structured routing fields — `related_tickers` for `cross_ticker`, `target_sector` for `sector` — with validator enforcement and a canonical 11-value sector enum from Neo4j. **Remove `scope_key` entirely from the schema** (it was vestigial — not routed, not deduped, redundant with `lesson`). Keep `_lookup_company_sector` (Neo4j) for current-ticker sector resolution and for stamping `source_sector` audit metadata at write time. Add structured include/exclude observability counters. Wipe derived learnings (clean slate), re-run 15 quarters chronologically.

---

## 1. What codex already did (full record, so we can revert if needed)

Codex produced a **stopgap** before this plan. The plan REPLACES it atomically, so no explicit revert is needed — the new commit deletes the stopgap pieces while keeping the one independently-valuable improvement it introduced (the `8k_packet.sector=None` fallback). This section documents the exact current state so a revert is trivial if desired.

### 1.1 Files touched by codex

| File | State | Action under this plan |
|---|---|---|
| `scripts/earnings/earnings_orchestrator.py` | **Modified** — 90 additions, 15 deletions (uncommitted, `git status: M`) | Partially superseded. Delete regex/matcher machinery; keep sector-lookup helper + `build_prediction_bundle` fallback. |
| `scripts/earnings/test_learning_context.py` | **New file, untracked** (not in `git ls-files`) | **Rewrite entirely** against the new schema. |
| `scripts/earnings/utils.py` | Pre-existing (committed in `8eb6d3b`). Codex only added an import FROM it. | Unchanged. |

### 1.2 Exact content codex added to `earnings_orchestrator.py`

Captured verbatim from `git diff scripts/earnings/earnings_orchestrator.py`:

**Imports added (lines 15–25):**
```python
import re                                                     # ADDED
from functools import lru_cache                               # ADDED
from typing import Any, Callable                              # Callable ADDED
```
```python
from scripts.earnings.utils import neo4j_session              # ADDED
```

**Module-level constant added (~line 114):**
```python
_COMPANY_SECTOR_QUERY = """
MATCH (c:Company {ticker: $ticker})
OPTIONAL MATCH (c)-[:BELONGS_TO]->(:Industry)-[:BELONGS_TO]->(sec:Sector)
RETURN coalesce(c.sector, sec.name) AS sector
"""
```

**Four new module-level functions added (~lines 126–193):**
```python
@lru_cache(maxsize=512)
def _lookup_company_sector(ticker: str) -> str | None:
    """Best-effort sector lookup for learning-context filtering."""
    # ...full body as in current file...

def _normalize_sector(sector: str | None) -> str | None:
    # ...whitespace/case normalization...

def _extract_scope_key_tickers(scope_key: Any) -> list[str]:
    """Extract explicit uppercase ticker tokens from a cross_ticker scope key."""
    # ...regex [A-Za-z]{1,5} + .isupper() filter...

def _cross_ticker_matches(entry, current_ticker, current_sector, sector_lookup) -> bool:
    """Keep only cross_ticker lessons with an explicit same-sector ticker anchor."""
    # ...direct-ticker OR same-sector-via-peer-lookup...
```

**`build_prediction_bundle` change (~line 258):**
```python
# BEFORE:
sector = (results.get("8k_packet") or {}).get("sector")

# AFTER (codex):
sector = (results.get("8k_packet") or {}).get("sector") or _lookup_company_sector(ticker)
```

**`build_learning_context` signature + filter change (~lines 2096, 2144–2155):**
```python
# Signature gained sector_lookup optional parameter:
def build_learning_context(ticker: str, sector: str | None = None,
                           base_dir: Path | None = None,
                           sector_lookup: Callable[[str], str | None] | None = None) -> dict:

# Filter body changed from:
    elif scope == "cross_ticker" and sector:
        pass                                    # OLD: silent drop

# To:
    elif scope == "cross_ticker" and _cross_ticker_matches(e, ticker, sector, lookup):
        cross_entries.append(e)                 # CODEX: regex-anchored
```

### 1.3 What codex created: `scripts/earnings/test_learning_context.py`

New 149-line untracked file with three `unittest.TestCase` tests:

1. `test_cross_ticker_includes_same_sector_explicit_peer` — sector-lookup driven inclusion.
2. `test_cross_ticker_keeps_direct_ticker_match_without_sector` — direct-ticker-match path.
3. `test_build_prediction_bundle_falls_back_to_company_sector_lookup` — builder's Neo4j fallback.

### 1.4 Revert procedure (if ever needed)

If you want to revert codex entirely before or after this plan lands:

```bash
# 1. Revert the orchestrator change
git checkout HEAD -- scripts/earnings/earnings_orchestrator.py

# 2. Delete the untracked test file
rm scripts/earnings/test_learning_context.py

# 3. Verify clean state
git diff scripts/earnings/earnings_orchestrator.py   # should show no diff
ls scripts/earnings/test_learning_context.py         # should not exist
```

The revert returns `build_learning_context` to its pre-codex state (cross_ticker silently dropped via `pass`), with sector-scope filtering still broken per §2.2. **We do NOT recommend reverting without a replacement** — codex's patch is a strict improvement over pre-codex state on the cross_ticker channel, even if superseded by this plan.

### 1.5 What from codex survives into the permanent fix

- **`_lookup_company_sector`** + `_COMPANY_SECTOR_QUERY` + `neo4j_session` import — kept. Used at write-time (stamping `source_sector`) AND at bundle-build time (current-ticker sector when `8k_packet.sector` is None).
- **`_normalize_sector`** — kept. Used for all sector-string comparisons.
- **`build_prediction_bundle` fallback** (`or _lookup_company_sector(ticker)`) — kept. Required because `8k_packet.sector` is chronically None (§2.3).
- **`lru_cache`, `Callable` imports** — kept if still used.

### 1.6 What from codex gets DELETED by the permanent fix

- **`_extract_scope_key_tickers`** — obsolete; routing is by structured `related_tickers` field.
- **`_cross_ticker_matches`** — obsolete; reader logic is 5 lines inline.
- **`sector_lookup` parameter** on `build_learning_context` — obsolete; reader no longer does per-entry sector lookups.
- **`import re`** — delete if not used elsewhere in the module.
- **Codex's `test_learning_context.py`** — rewrite entirely against the new schema.

---

## 2. Problems solved (with concrete evidence)

### 2.1 Silent drop of every `cross_ticker` entry (pre-codex)

Reader code had `elif scope == "cross_ticker" and sector: pass` — every entry discarded. Writer and validator worked correctly; storage preserved entries; predictor never saw them.

**Direct evidence**: 10+ cross_ticker entries in the existing calibration corpus (AVGO, BURL) never reached any predictor. Examples:

- `Companies/AVGO/events/Q3_FY2023/attribution/result.json` → `scope_key="conglomerate_earnings"` (lesson about diversified-issuer veto-condition). Never reached TXN, MCHP, or ADI predictors.
- `Companies/BURL/events/Q1_FY2025/attribution/result.json` → `scope_key="ROST_BURL"` (lesson about peer-quality-match). Never reached ROST predictor.
- `Companies/BURL/events/Q2_FY2025/attribution/result.json` → `scope_key="sequential_beat_quality"` (cross-industry generalization). Never reached any predictor.

### 2.2 Silent drop on the `sector` scope via raw-equality match

Reader code: `if scope == "sector" and sector and e.get("scope_key") == sector`. Raw string equality.

**Direct evidence from real learner output**:
- AVGO Q3_FY2023 sector-scope: `scope_key="semiconductors"`. Neo4j sector for AVGO: `Technology`. `"semiconductors" != "Technology"` → silently dropped.
- AVGO Q4_FY2023 sector-scope: `scope_key="post_rally_earnings"`. Not a sector at all. Silently dropped.
- BURL Q1_FY2025 sector-scope: `scope_key="off_price_retail"`. Neo4j: `ConsumerCyclical`. Silently dropped.
- BURL Q2_FY2025 sector-scope: `scope_key="off_price_retail"`. Silently dropped.

The learner is using `scope_key` as an industry/theme tag, NOT as a canonical sector label. The plan never constrained it to be a canonical label. Result: sector-scope channel was nearly as broken as cross_ticker.

### 2.3 `8k_packet.sector = None` on all 15 calibration bundles

Verified via a script over every `prediction/context_bundle.json`:

```
AVGO: 5/5 quarters → sector=None
NVDA: 5/5 quarters → sector=None
BURL: 5/5 quarters → sector=None
```

**Root cause**: `builder_adapters.build_8k_packet` delegates to the legacy `warmup_cache.build_8k_packet`, which does not populate `sector`. `_enrich_packet` adds PIT metadata but not sector. This means `build_prediction_bundle` could NEVER know the current ticker's sector without an external Neo4j lookup — so codex's `or _lookup_company_sector(ticker)` fallback is load-bearing, not optional.

### 2.4 Observability: zero

No log, no metric, no test covered ANY of these silent drops. The only reason this bug was discovered was manual code review.

### 2.5 `scope_key` doing double duty

`scope_key` simultaneously (a) identifies the routing target (e.g., sector name) and (b) carries a human-readable theme tag. These are incompatible jobs. The cleanest fix is to introduce structured routing fields (`target_sector`, `related_tickers`) — and then **remove `scope_key` entirely**, because once routing is structured the field has no remaining job (it's not routed, not deduped, and duplicates information already carried by `lesson`).

---

## 3. Canonical sector enum — from Neo4j audit

Verified 2026-04-17 against the live Neo4j graph:

```
Technology              (n=162)
Healthcare              (n=145)
ConsumerCyclical        (n=121)
Industrials             (n=110)
FinancialServices       (n=54)
ConsumerDefensive       (n=44)
RealEstate              (n=36)
Energy                  (n=35)
BasicMaterials          (n=34)
CommunicationServices   (n=30)
Utilities               (n=25)
─────────────────────────────
TOTAL                   796 companies (zero NULLs within the universe)
```

- Both `Company.sector` property AND `Industry→Sector` relationship yield the same 11 values.
- `coalesce(c.sector, sec.name)` is robust — both paths return identical labels.
- Three FAANG tickers return None (`MSFT`, `GOOGL`, `META`) because they're OUT of the 796-company universe. Harmless: `source_ticker` in `append_global_lessons` is always a current-run ticker (which IS in the universe).

### 3.1 How the enum lives in code — `config/canonical_sectors.py` (NEW)

**Single hardcoded Python constant + pre-commit consistency test** — the best-of-both-worlds design.

- **Why hardcode**: validator runs inside a stdlib-only PreToolUse hook; adding Neo4j at validate-time would break the fail-closed invariant. SKILL.md must enumerate the list in prose for the LLM anyway. A Neo4j-unreachable event must never silently permit arbitrary sector strings.
- **Why not stale**: a pre-commit consistency test queries Neo4j and compares the live distinct-sector set against the hardcoded enum. Any drift fails CI loudly with a specific action ("update `config/canonical_sectors.py` and SKILL.md").

**Module:**

```python
# config/canonical_sectors.py  (new file)
"""Canonical sector labels — hardcoded runtime enum, CI-verified against Neo4j.

Single source of truth for the validator + SKILL.md prose list. Runtime
has zero Neo4j dependency. A pre-commit test (test_canonical_sectors_consistency.py)
fails loudly if Neo4j's distinct sector set ever diverges from this enum.
"""
from __future__ import annotations

CANONICAL_SECTORS: frozenset[str] = frozenset({
    "Technology",
    "Healthcare",
    "ConsumerCyclical",
    "Industrials",
    "FinancialServices",
    "ConsumerDefensive",
    "RealEstate",
    "Energy",
    "BasicMaterials",
    "CommunicationServices",
    "Utilities",
})
```

**Imported by** `validate_attribution.py` (single import, replaces the inline `_CANONICAL_SECTORS` block shown in §6.1).

**Hook compatibility note**: `config/canonical_sectors.py` lives at the repo root, not inside `scripts/earnings/`. The PreToolUse hook (`.claude/hooks/validate_attribution_output.py`) currently only adds `scripts/earnings` to `sys.path`. It MUST be modified to add `project_dir` itself first — otherwise `from config.canonical_sectors import CANONICAL_SECTORS` fails under hook execution, triggering fail-closed behavior and blocking every learner write. See §5 file inventory row 3.

### 3.2 `_lookup_company_sector` — only cache successes (anti-poisoning)

The existing helper (kept from codex) uses `@lru_cache(maxsize=512)`. This caches every return value — including `None` on transient Neo4j failures. For unmonitored runs, a single Neo4j hiccup at startup could poison the cache for the entire session.

**Fix**: replace `@lru_cache` with a manual dict cache that only stores successful lookups. Failed/None lookups re-query every time (bounded by LRU eviction would also be fine, but the manual dict is simpler and the universe is 796 entries).

```python
# scripts/earnings/earnings_orchestrator.py
_SECTOR_CACHE: dict[str, str] = {}  # module-level, successes ONLY

def _lookup_company_sector(ticker: str) -> str | None:
    """Sector lookup. Only successful results are cached — None results re-query
    on every call so transient Neo4j failures cannot poison the cache."""
    symbol = str(ticker or "").upper().strip()
    if not symbol:
        return None
    if symbol in _SECTOR_CACHE:
        return _SECTOR_CACHE[symbol]

    try:
        with neo4j_session() as (session, err):
            if err or session is None:
                log.warning("Sector lookup unavailable for %s: %s", symbol, err)
                return None  # NOT cached
            row = session.run(_COMPANY_SECTOR_QUERY, ticker=symbol).single()
    except Exception as e:
        log.warning("Sector lookup failed for %s: %s", symbol, e)
        return None  # NOT cached

    if not row:
        return None
    sector = (row.data().get("sector") or "").strip()
    if not sector:
        return None
    _SECTOR_CACHE[symbol] = sector  # successes only
    return sector
```

Behavior: successful lookup for AAPL caches `"Technology"`; subsequent calls O(1). If Neo4j is down when we first call for AAPL, we log + return None, and the next AAPL call actually retries. No session-long poisoning.

**pre-commit consistency tests** — see §7.5.

**This 11-value enum is frozen and shipped verbatim into SKILL.md + validator.** If Neo4j's sector list ever changes, the validator + SKILL.md must be updated together.

---

## 4. Final schema contract — every field, every scope

### 4.1 Learner-authored fields (in `attribution/result.json::global_observations[]`)

**`scope_key` is REMOVED from the schema** (amendment 2026-04-17). It was vestigial — not used by the router, the dedupe step, the validator's logic, or any predictor action. `lesson` is the content; routing fields are structured. Nothing made up, nothing unused.

#### `scope = "cross_ticker"`
```json
{
  "scope": "cross_ticker",
  "related_tickers": ["AAA", "BBB"],
  "lesson": "..."
}
```
- `related_tickers`: **REQUIRED, non-empty**, list of uppercase alphabetic strings, each 1–5 chars, **max 8 entries**. Duplicate rejection is **validator-authoritative** (writer does not dedupe — validator fails the write and triggers learner retry on duplicates).
- `target_sector`, `scope_key`: **MUST NOT be present.** Validator rejects if present.

#### `scope = "sector"`
```json
{
  "scope": "sector",
  "target_sector": "Technology",
  "lesson": "..."
}
```
- `target_sector`: **REQUIRED**, must be exactly one of the 11 canonical enum values in §3 (imported from `config.canonical_sectors`). Validator rejects any other value.
- `related_tickers`, `scope_key`: **MUST NOT be present.** Validator rejects if present.

#### `scope = "macro"`
```json
{
  "scope": "macro",
  "lesson": "..."
}
```
- `related_tickers`, `target_sector`, `scope_key`: **MUST NOT be present.** Validator rejects any of them.

### 4.2 Python-stamped fields (added by `append_global_lessons` to `learnings/global.json::entries[]`)

Applied uniformly to every entry regardless of scope:

| Field | Source | Purpose |
|---|---|---|
| `source_ticker` | `attribution_result.ticker` | Audit: which ticker's learner produced this lesson |
| `source_sector` | `_lookup_company_sector(source_ticker)` | Audit ONLY. **Not used for routing.** May be `None` if Neo4j lookup fails; that's fine — filter never reads it. |
| `quarter_label` | `attribution_result.quarter_label` | Audit |
| `attributed_at` | `attribution_result.attributed_at` | Used for recency sort at read time |

### 4.3 Reader routing logic (exact)

```python
normalized_current_sector = _normalize_sector(sector)

for e in entries:
    scope = e.get("scope")
    if scope == "sector":
        if normalized_current_sector and \
           _normalize_sector(e.get("target_sector")) == normalized_current_sector:
            sector_entries.append(e)
        else:
            excluded["sector_mismatch"] += 1

    elif scope == "macro":
        macro_entries.append(e)

    elif scope == "cross_ticker":
        if ticker in (e.get("related_tickers") or []):
            cross_entries.append(e)
        else:
            excluded["cross_ticker_not_listed"] += 1

    else:
        excluded["unknown_scope"] += 1
```

**Design invariants — MUST hold in every future change:**
- Routing fields are structured. No regex. No free-string matching. No Neo4j calls inside the per-entry filter.
- `scope_key` is NEVER read by the routing logic for any scope.
- `source_sector` is NEVER read by the routing logic.
- Every exclusion increments a named counter. No silent drops.

### 4.4 Per-scope caps (unchanged from current)

After recency sort and dedupe by lesson-text-normalized:
- `sector_entries[:4]`
- `macro_entries[:4]`
- `cross_entries[:2]`

Total: ≤10 global entries rendered into bundle Section 10.

### 4.5 Observability contract

Emitted once per `build_learning_context` call — ALWAYS (even when `global.json` is absent):

```
log.info(
    "learning_context %s(sector=%s): "
    "included[sector=%d macro=%d cross=%d] "
    "excluded[sector_mismatch=%d current_sector_unknown=%d "
    "cross_ticker_not_listed=%d cross_ticker_missing_related=%d "
    "unknown_scope=%d legacy_schema=%d]",
    ticker, sector,
    len(sector_entries), len(macro_entries), len(cross_entries),
    excluded["sector_mismatch"],
    excluded["current_sector_unknown"],
    excluded["cross_ticker_not_listed"],
    excluded["cross_ticker_missing_related"],
    excluded["unknown_scope"],
    excluded["legacy_schema"],
)
```

**Six named exclusion counters, all zero by default** (so the log line is fully populated even in the empty-file case):

| Counter | Fires when |
|---|---|
| `sector_mismatch` | Entry's `target_sector` is present and valid but does not match the current ticker's sector |
| `current_sector_unknown` | The current ticker's sector is None/empty, so sector-scope filtering cannot run |
| `cross_ticker_not_listed` | Entry's `related_tickers` is non-empty but does not contain the current ticker |
| `cross_ticker_missing_related` | Entry has `scope="cross_ticker"` but no `related_tickers` (legacy/malformed) |
| `unknown_scope` | Entry's `scope` is not one of `sector`/`macro`/`cross_ticker` |
| `legacy_schema` | Sector-scope entry missing `target_sector` (old-schema residue post-wipe) |

**Absent-file case**: when `global.json` does not exist (e.g., immediately post-wipe), the function still emits the log line with all counters at zero and all included counts at zero. This guarantees there is never a "silent silence" where nothing at all is logged — the operator can always see the filter fired.

Any future silent-drop regression appears immediately as an anomalous exclusion count.

---

## 5. File-by-file change inventory (single atomic commit)

| # | File | Action | Lines touched (approx) |
|---|---|---|---|
| 1 | `config/canonical_sectors.py` | **NEW** — single hardcoded `CANONICAL_SECTORS` frozenset. Imported by validator. Per §3.1. | +20 |
| 2 | `scripts/earnings/validate_attribution.py` | **Add** strict validation block per §6.1: required fields by scope, rejected fields by scope (including `scope_key` universally), enum check on `target_sector` via `from config.canonical_sectors import CANONICAL_SECTORS`, shape check + **duplicate rejection** on `related_tickers`. | +45 |
| 3 | `.claude/hooks/validate_attribution_output.py` | **Modify** — add `sys.path.insert(0, project_dir)` BEFORE the existing `scripts/earnings` insert so the validator can import `from config.canonical_sectors import CANONICAL_SECTORS` under hook execution. Without this, the hook fails-closed on import and blocks every learner write. | +1 |
| 4 | `scripts/earnings/earnings_orchestrator.py::append_global_lessons` | **Modify** — stamp `source_sector` via `_lookup_company_sector`; pass through `related_tickers` and `target_sector`; **drop `scope_key` pass-through**; **convert to upsert-by-`(source_ticker, quarter_label)`** per §6.2. | +12 |
| 5 | `scripts/earnings/earnings_orchestrator.py::append_ticker_lesson` | **Modify** — convert to upsert-by-`quarter_label` so re-runs don't duplicate entries. Per §6.2. | +5 |
| 6 | `scripts/earnings/earnings_orchestrator.py::build_learning_context` | **Modify** — replace filter body with §4.3 / §6.3 structured logic; add exclusion counters; drop `sector_lookup` parameter; normalize sector on both sides; **log on `except` paths** (no silent infrastructure failure). | +25 / −15 |
| 7 | `scripts/earnings/earnings_orchestrator.py` deletions | **Delete** `_extract_scope_key_tickers` + `_cross_ticker_matches`. Remove `import re` if no other use. Remove `Callable` from typing import if no other use. Remove `sector_lookup` callable threading anywhere else. | −40 |
| 8 | `scripts/earnings/earnings_orchestrator.py::_render_learning_context` | **Modify** — split single "### Cross-Ticker Insights" heading into three sub-sections; **drop all `scope_key` display references** (field removed from schema). | +15 / −8 |
| 9 | `scripts/earnings/earnings_orchestrator.py` — add observability log | Insert the §4.5 log line just before `return result`. Include the `excluded` dict initialization at start of filter block. | +8 |
| 10 | `.claude/skills/earnings-learner/SKILL.md` | **Modify** — update "Global observations" section per §6.7: **remove `scope_key` from required fields everywhere**; document `target_sector` enum (imported value list) and `related_tickers` shape rules. Add three worked examples. | +30 / −15 |
| 11 | `.claude/plans/learner.md` §8 + §9 | **Modify** — update schema JSON blocks and filter description to match new contract (no `scope_key`). Reference this plan as the authoritative source for global-lessons routing. | +20 / −30 |
| 12 | `scripts/earnings/test_learning_context.py` | **Rewrite entirely** — drop codex's regex-based tests. Add R1–R15 per §7.3, W1–W8 per §7.2, I1–I10 per §7.4 (I10 is the informed-retry H2 acceptance gate). | +270 / −149 |
| 13 | `scripts/earnings/test_validate_attribution.py` | **New file** — V1–V20 validator tests per §7.1 (including `scope_key`-rejection test V19 and duplicate-rejection test V20). | +200 |
| 14 | `scripts/earnings/test_canonical_sectors_consistency.py` | **New file** — CS1–CS3 per §7.5: Neo4j ↔ module parity, SKILL.md ↔ module parity, module self-consistency. Required in pre-commit checklist (§8.1); see §10 for CI-workflow status. | +60 |
| 15 | Data wipe | `cp -r earnings-analysis/learnings earnings-analysis/learnings.backup.$(date +%s)` then `rm earnings-analysis/learnings/global.json earnings-analysis/learnings/ticker/*.json`. NOT committed; operator action. | — |

**Net code change**: ~+520 / −260. Net +260 lines from today's state (adds tests, consistency checker, canonical module; deletes regex machinery and `scope_key` threading).

### 5.1 External consumer surface — audited and bounded

Grep across the repo for `global.json|learnings/ticker|related_tickers|source_sector|global_observations|target_sector|cross_ticker` confirms the ONLY code consumers of these schemas are:

- `scripts/earnings/earnings_orchestrator.py`
- `scripts/earnings/validate_attribution.py`
- `.claude/skills/earnings-learner/SKILL.md`
- `scripts/earnings/test_learning_context.py`

Docs-only references (no code impact):
- `.claude/plans/learner.md`, `.claude/plans/earnings-orchestrator.md`, `.claude/plans/obsidian_thinking.md`, `.claude/plans/trade-execution-system.md`
- `learning-loop-explainer.html`, `trade-system-explorer.html`

False-positive hits (unrelated):
- `eventReturns/polygonClass.py` — `related_tickers` is a local Polygon-API variable, not our schema
- `scripts/run_burl_ab_sequential.py`, `scripts/run_nvda_ab_sequential.py` — docstring mentions only
- `neograph/Neo4jInitializer.py` — irrelevant string match

**No hidden readers. Change surface fully enumerated.**

---

## 6. Implementation details (exact code snippets)

### 6.1 `validate_attribution.py` — new block

Imports from the single-source-of-truth module added in §3.1:

```python
from config.canonical_sectors import CANONICAL_SECTORS

def _ok_ticker(t: object) -> bool:
    return isinstance(t, str) and t.isupper() and t.isalpha() and 1 <= len(t) <= 5

_MAX_RELATED_TICKERS = 8
_REJECTED_SCOPE_KEY_MSG = "scope_key has been removed from the schema; do not emit"

# ... inside the loop over global_observations entries:
scope = obs.get("scope")
rt = obs.get("related_tickers")
ts = obs.get("target_sector")
sk = obs.get("scope_key")  # ← must never be present in the new schema

# scope_key removed from schema (amendment 2026-04-17). Reject if present,
# across ALL scopes, so learner output is forced to converge to the new shape.
if sk is not None:
    errors.append(f"global_observations[{i}].scope_key: {_REJECTED_SCOPE_KEY_MSG}")

if scope == "cross_ticker":
    if not isinstance(rt, list) or not rt:
        errors.append(f"global_observations[{i}].related_tickers must be a non-empty list for cross_ticker")
    else:
        if len(rt) > _MAX_RELATED_TICKERS:
            errors.append(f"global_observations[{i}].related_tickers exceeds cap {_MAX_RELATED_TICKERS} (got {len(rt)})")
        bad = [t for t in rt if not _ok_ticker(t)]
        if bad:
            errors.append(f"global_observations[{i}].related_tickers contains invalid tickers: {bad}")
        # Validator-authoritative dedupe (writer does NOT dedupe):
        if len(set(rt)) != len(rt):
            errors.append(f"global_observations[{i}].related_tickers contains duplicates")
    if ts is not None:
        errors.append(f"global_observations[{i}].target_sector must not be present for cross_ticker scope")

elif scope == "sector":
    if not isinstance(ts, str) or ts not in CANONICAL_SECTORS:
        errors.append(
            f"global_observations[{i}].target_sector must be one of "
            f"{sorted(CANONICAL_SECTORS)} (got {ts!r})"
        )
    if rt is not None:
        errors.append(f"global_observations[{i}].related_tickers must not be present for sector scope")

elif scope == "macro":
    if rt is not None:
        errors.append(f"global_observations[{i}].related_tickers must not be present for macro scope")
    if ts is not None:
        errors.append(f"global_observations[{i}].target_sector must not be present for macro scope")
```

**"Did you mean" hints (H3, amendment 2026-04-17)** — because the system runs unmonitored with no escape hatch, validator error messages must be actionable enough that the 1-retry path (H2) can self-correct. Use stdlib `difflib` only; no new dependencies:

```python
from difflib import get_close_matches

# For target_sector: if the value is a string but not in the enum, suggest canonicals:
if isinstance(ts, str) and ts not in CANONICAL_SECTORS:
    suggestions = get_close_matches(ts, CANONICAL_SECTORS, n=2, cutoff=0.5)
    hint = f" (did you mean: {', '.join(repr(s) for s in suggestions)}?)" if suggestions else ""
    errors.append(
        f"global_observations[{i}].target_sector must be one of "
        f"{sorted(CANONICAL_SECTORS)} (got {ts!r}){hint}"
    )

# For related_tickers: if a string is provided instead of a list, suggest the list form.
# REGEX-FREE: uses str.translate + split on a known separator set so the "no regex
# anywhere in the fix" invariant holds even in the error-hint path.
_RELATED_TICKERS_SEPARATORS = "_ ,/|-"
_RELATED_TICKERS_SEP_TABLE = str.maketrans({c: " " for c in _RELATED_TICKERS_SEPARATORS})

if scope == "cross_ticker" and isinstance(rt, str):
    normalized = rt.upper().translate(_RELATED_TICKERS_SEP_TABLE)
    tokens = [t for t in normalized.split() if _ok_ticker(t)]
    hint = f" (did you mean: {tokens!r}?)" if tokens else ""
    errors.append(
        f"global_observations[{i}].related_tickers must be a list, got string {rt!r}{hint}"
    )
```

**Regex policy in the final design — zero regex anywhere.** The deleted `_extract_scope_key_tickers` / `_cross_ticker_matches` machinery used regex as a routing oracle. That's gone. The validator's error-hint path that previously used `re.split` now uses `str.translate` + `str.split` on a known separator set — no regex, same behavior, cleaner invariant. After this commit, `grep -n '\bimport re\b\|\bre\.' scripts/earnings/validate_attribution.py scripts/earnings/earnings_orchestrator.py` MUST return nothing related to learning-context routing.

**Duplicate authority rule (clarified 2026-04-17)**: the validator is the SINGLE authority on `related_tickers` shape — non-empty, uppercase 1–5 char, max 8, **no duplicates**. The writer is a pure pass-through; it does NOT dedupe. Rationale: fail fast, retry the learner, converge to clean output. Silent writer-side dedupe would mask authoring errors instead of signaling them back for correction.

### 6.2 `append_global_lessons` — stamping additions

```python
for obs in observations:
    enriched.append({
        "scope":            obs.get("scope"),
        # NOTE: scope_key removed from schema (amendment 2026-04-17).
        #       Writer does NOT pass it through. Validator rejects it on writes.
        # Pass-through structured routing fields:
        "related_tickers":  obs.get("related_tickers"),   # may be None (non-cross_ticker)
        "target_sector":    obs.get("target_sector"),     # may be None (non-sector)
        # Existing audit fields:
        "source_ticker":    attribution_result.get("ticker"),
        # source_sector audit metadata (NOT routing):
        "source_sector":    _lookup_company_sector(attribution_result.get("ticker")),
        "quarter_label":    attribution_result.get("quarter_label"),
        "attributed_at":    attribution_result.get("attributed_at"),
        "lesson":           obs.get("lesson"),
    })
```

**Idempotent upsert (NEW, amendment 2026-04-17)** — the current append functions are pure-append; on derived-write recovery or any re-run they accumulate duplicate entries in `global.json` / `ticker.json`. Replace pure `.append` / `.extend` with **upsert-by-source-key**, AND **remove the early-return when `observations` is empty** so that a re-run producing zero global observations still deletes any stale entries for that quarter:

```python
# append_global_lessons — idempotent by (source_ticker, quarter_label).
# IMPORTANT: do NOT early-return when observations == []. A re-run that
# produces zero global_observations must still purge any prior entries
# for (source_ticker, quarter_label), otherwise stale entries survive forever.
observations = attribution_result.get("global_observations", [])
enriched = [
    {
        "scope":            obs.get("scope"),
        "related_tickers":  obs.get("related_tickers"),
        "target_sector":    obs.get("target_sector"),
        "source_ticker":    attribution_result.get("ticker"),
        "source_sector":    _lookup_company_sector(attribution_result.get("ticker")),
        "quarter_label":    attribution_result.get("quarter_label"),
        "attributed_at":    attribution_result.get("attributed_at"),
        "lesson":           obs.get("lesson"),
    }
    for obs in observations
]

path = LEARNINGS_DIR / "global.json"
path.parent.mkdir(parents=True, exist_ok=True)

lock_path = path.with_suffix(".lock")
with open(lock_path, "w") as lock_fd:
    fcntl.flock(lock_fd, fcntl.LOCK_EX)
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = {"schema_version": "global_lessons.v1", "updated_at": None, "entries": []}

        # Upsert step — always runs, even when enriched is []:
        key = (attribution_result["ticker"], attribution_result["quarter_label"])
        data["entries"] = [e for e in data["entries"]
                           if (e.get("source_ticker"), e.get("quarter_label")) != key]
        data["entries"].extend(enriched)
        data["updated_at"] = attribution_result.get("attributed_at")
        _atomic_write_json(path, data)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
return path

# append_ticker_lesson — idempotent by quarter_label:
target_ql = entry["quarter_label"]
data["lessons"] = [l for l in data["lessons"]
                   if l.get("quarter_label") != target_ql]
data["lessons"].append(entry)
```

This converts "append" semantics to "upsert by source key." First write for a quarter: unchanged. Re-run producing the same set: replaced in place. Re-run producing zero observations: stale entries **purged**. Reader-side dedupe (`_dedupe` by normalized lesson text) still provides a defense-in-depth layer for routing correctness.

**Contract change (explicit)**: `append_global_lessons` used to be documented as *"Returns the path written, or None if no observations."* After this amendment, it **always** returns the path — including in the zero-observations case, where the function still performs the flock-protected upsert to purge any stale entries. Update the docstring to match. Any caller that checked `result is None` as an "empty observations" signal must be updated; a grep of the current repo shows `run_learner_for_quarter` is the only caller and it doesn't condition on the return value, so no caller-side change is needed beyond the docstring.

**Ground-truth note (verified 2026-04-17 by sanity-check read)**: the current `append_global_lessons` enrichment dict at lines 2060–2067 of `earnings_orchestrator.py` does NOT stamp `source_sector` at all — it only contains `scope, scope_key, source_ticker, quarter_label, attributed_at, lesson`. Adding `source_sector` is a pure **field addition**, not a replacement of an existing value; there is no prior source_sector to migrate. The `scope_key` drop is the only field removal. The return-type annotation `-> Path | None` stays as-is (the function can still return None if an exception propagates after the lock releases; the functional contract "always returns path on success" is documented in the docstring, not the type signature). Minimal-diff principle.

**`_lookup_company_sector` behavior**: see §3.2 — the `@lru_cache` decorator is replaced with a manual dict cache that stores ONLY successful lookups, and None-returning paths emit `log.warning`. Any reference to `@lru_cache` on this helper is an old-codex artifact; the authoritative spec is §3.2.

### 6.3 `build_learning_context` — full replacement for the global-filter block

```python
# ── Global lessons: structured-field routing, per-scope caps ──
# Counters are initialized to zero BEFORE the file-exists check so the
# log line at the end always fires with a full, consistent shape —
# even if global.json is absent (first-ever run, post-wipe state).
sector_entries = []
macro_entries = []
cross_entries = []
excluded = {
    "sector_mismatch": 0,
    "current_sector_unknown": 0,
    "cross_ticker_not_listed": 0,
    "cross_ticker_missing_related": 0,
    "unknown_scope": 0,
    "legacy_schema": 0,
}
normalized_current_sector = _normalize_sector(sector)

if global_path.exists():
    try:
        data = json.loads(global_path.read_text(encoding="utf-8"))
        entries = data.get("entries", [])

        for e in entries:
            scope = e.get("scope")

            if scope == "sector":
                ts = e.get("target_sector")
                if ts is None:
                    # Legacy/old-schema entry (pre-fix) — transparently excluded
                    excluded["legacy_schema"] += 1
                    continue
                if not normalized_current_sector:
                    # The CURRENT ticker's sector is unknown — cannot route sector-scope.
                    # (Not to be confused with legacy_schema, which is about the ENTRY.)
                    excluded["current_sector_unknown"] += 1
                    continue
                if _normalize_sector(ts) == normalized_current_sector:
                    sector_entries.append(e)
                else:
                    excluded["sector_mismatch"] += 1

            elif scope == "macro":
                macro_entries.append(e)

            elif scope == "cross_ticker":
                rt = e.get("related_tickers")
                if not rt:
                    # Legacy/old-schema entry OR learner error past validator — excluded
                    excluded["cross_ticker_missing_related"] += 1
                    continue
                if ticker in rt:
                    cross_entries.append(e)
                else:
                    excluded["cross_ticker_not_listed"] += 1

            else:
                excluded["unknown_scope"] += 1

        # Sort by recency, dedupe by normalized lesson text, apply caps
        for bucket in (sector_entries, macro_entries, cross_entries):
            bucket.sort(key=lambda x: x.get("attributed_at", ""), reverse=True)

        def _dedupe(items):
            seen = set()
            out = []
            for item in items:
                k = (item.get("lesson") or "").strip().lower()
                if k and k not in seen:
                    seen.add(k)
                    out.append(item)
            return out

        sector_entries = _dedupe(sector_entries)[:4]
        macro_entries  = _dedupe(macro_entries)[:4]
        cross_entries  = _dedupe(cross_entries)[:2]

        result["global_lessons"] = sector_entries + macro_entries + cross_entries
    except json.JSONDecodeError as e:
        # Amendment 2026-04-17: no silent failures, even on infrastructure errors.
        log.error("global.json malformed — no global lessons loaded for %s: %s", ticker, e)
    except OSError as e:
        log.error("global.json read failed — no global lessons loaded for %s: %s", ticker, e)

# Observability log — fires ALWAYS, even when global_path didn't exist.
# Names must match §4.5 contract exactly. Six exclusion counters, all initialized
# to zero so the log line shape is stable on any code path.
log.info(
    "learning_context %s(sector=%s): "
    "included[sector=%d macro=%d cross=%d] "
    "excluded[sector_mismatch=%d current_sector_unknown=%d "
    "cross_ticker_not_listed=%d cross_ticker_missing_related=%d "
    "unknown_scope=%d legacy_schema=%d]",
    ticker, sector,
    len(sector_entries), len(macro_entries), len(cross_entries),
    excluded["sector_mismatch"],
    excluded["current_sector_unknown"],
    excluded["cross_ticker_not_listed"],
    excluded["cross_ticker_missing_related"],
    excluded["unknown_scope"],
    excluded["legacy_schema"],
)
```

**Note**: the analogous `except` block on the ticker-lessons read block above this section must also log on failure. Both paths preserve the defensive "predictor bundle still builds even if lessons unavailable" semantics, but now log operator-visible errors instead of silently returning empty lessons. `log.error` is deliberate (not `warning`) — a corrupted `global.json` or disk read failure is an infrastructure incident, not a routine condition.

### 6.4 `_render_learning_context` — heading split (scope_key removed)

```python
# Replace the single-heading global section with three sub-sections.
# scope_key is no longer in the schema; rendering uses routing fields only.
if global_lessons:
    by_scope = {"sector": [], "macro": [], "cross_ticker": []}
    for entry in global_lessons:
        by_scope.setdefault(entry.get("scope"), []).append(entry)

    if by_scope["sector"]:
        parts.append(f"\n### Sector Lessons ({len(by_scope['sector'])} entries)\n")
        for entry in by_scope["sector"]:
            ts = entry.get("target_sector") or "?"
            src = entry.get("source_ticker") or "?"
            parts.append(f"- [sector:{ts}] ({src}) {entry.get('lesson','')}")

    if by_scope["macro"]:
        parts.append(f"\n### Macro Lessons ({len(by_scope['macro'])} entries)\n")
        for entry in by_scope["macro"]:
            src = entry.get("source_ticker") or "?"
            parts.append(f"- [macro] ({src}) {entry.get('lesson','')}")

    if by_scope["cross_ticker"]:
        parts.append(f"\n### Cross-Ticker Lessons ({len(by_scope['cross_ticker'])} entries)\n")
        for entry in by_scope["cross_ticker"]:
            rt = entry.get("related_tickers") or []
            src = entry.get("source_ticker") or "?"
            parts.append(f"- [cross:{','.join(rt)}] ({src}) {entry.get('lesson','')}")
```

### 6.5 Deletions

Remove entire function bodies:
- `_extract_scope_key_tickers` (lines ~160–171)
- `_cross_ticker_matches` (lines ~174–193)

Remove `sector_lookup` parameter from `build_learning_context` signature and all internal references (`lookup = sector_lookup or _lookup_company_sector` line).

Remove `import re` if no other occurrence in the file. Verify with grep.

Remove `Callable` from `typing import` if no other occurrence.

### 6.6 Informed-retry prompt (H2 — compensating hardening for no-escape-hatch design)

Because this pipeline runs unmonitored and has no permissive fallback, the 1-retry path in `run_learner_for_quarter` MUST be informed by the prior validation errors, not a blind re-run with the same prompt. This is the H2 hardening referenced in R1 mitigation (§9).

**Signature changes** — three functions gain one optional parameter each:

```python
# scripts/earnings/earnings_orchestrator.py

def _build_learner_prompt(
    skill_content: str,
    ticker: str,
    quarter_info: dict,
    actual_return: dict,
    pit_mode: str,
    pit_cutoff: str | None,
    pit_boundary_source: str,
    result_path: Path,
    prediction_result_path: Path,
    context_bundle_path: Path,
    prior_lessons_path: Path,
    prior_validation_errors: list[str] | None = None,  # NEW
) -> str:
    inputs_section = f"""--- INPUTS ---
TICKER: {ticker}
QUARTER: {quarter_info.get('quarter_label', 'UNKNOWN')}
...
"""
    if prior_validation_errors:
        numbered = "\n".join(f"  {i+1}. {e}" for i, e in enumerate(prior_validation_errors))
        retry_block = (
            "\n--- YOUR PRIOR OUTPUT WAS REJECTED ---\n"
            "The previous attempt failed schema validation with these errors:\n"
            f"{numbered}\n\n"
            "Fix these EXACT errors and re-emit attribution/result.json. "
            "Do not change other fields; only correct the listed shape issues.\n"
        )
        return f"{skill_content}\n\n{inputs_section}{retry_block}"
    return f"{skill_content}\n\n{inputs_section}"


async def _run_learner_via_sdk(
    ..., prior_validation_errors: list[str] | None = None,  # NEW
) -> str | None:
    ...
    prompt = _build_learner_prompt(..., prior_validation_errors=prior_validation_errors)
    ...


def run_learner_via_sdk(
    ..., prior_validation_errors: list[str] | None = None,  # NEW
) -> str | None:
    return asyncio.run(_run_learner_via_sdk(..., prior_validation_errors=prior_validation_errors))
```

**Retry call site change** in `run_learner_for_quarter` — the existing retry block:

```python
# BEFORE (blind retry):
if errors:
    log.error("Learner failed %s %s: validation errors: %s", ...)
    result_path.unlink(missing_ok=True)
    log.info("Retrying learner for %s %s (1 retry)", ...)
    run_learner_via_sdk(ticker=ticker, quarter_info=quarter_info, ...)  # same args

# AFTER (informed retry):
if errors:
    log.error("Learner failed %s %s: validation errors: %s", ticker, ql, "; ".join(errors[:3]))
    result_path.unlink(missing_ok=True)
    log.info("Retrying learner for %s %s (1 retry, feeding %d validation errors back)",
             ticker, ql, len(errors))
    run_learner_via_sdk(
        ticker=ticker,
        quarter_info=quarter_info,
        actual_return=actual_return,
        pit_mode=pit_mode,
        pit_cutoff=pit_cutoff,
        pit_boundary_source=pit_boundary_source,
        result_path=result_path,
        prediction_result_path=attr_paths["prediction_result_path"],
        context_bundle_path=attr_paths["context_bundle_path"],
        prior_lessons_path=learn_paths["ticker_lessons_path"],
        prior_validation_errors=errors,  # NEW — informs the retry
    )
```

**Why this is the real replacement for `STRICT_SCHEMA`**:

| Property | Escape hatch (rejected) | Informed retry (chosen) |
|---|---|---|
| Fail-safe if learner can't produce new schema | Silent permissive mode — pollutes data | Fails loudly; ticker chain stops |
| Observable | Might flip ON and stay on for weeks | Every retry logs exactly what was fed back |
| Reversible | Operator must remember to flip OFF | Stateless — nothing to forget |
| Improves over time | No | LLMs correct schema errors ~100% when shown the errors |

**Integration test coverage** — formal row added to the §7.4 matrix as **I10**: verifies a deliberately-malformed first attempt followed by an informed retry succeeds. This is the acceptance gate for H2 — the informed-retry mechanism is not optional prose, it is a required test in the atomic commit. See §7.4 row I10.

**Net change for H2**: ~15 lines across 3 function signatures + 1 block at the retry site. Zero new dependencies. Replaces the rejected `STRICT_SCHEMA` escape hatch with an active correction mechanism that makes the "must be perfect in first go" constraint structurally achievable.

**Ground-truth note (verified 2026-04-17 by sanity-check read)**: the H2 amendment applies to the FIRST retry only (lines 1912–1929 of `run_learner_for_quarter`). The existing SECOND-validation block at lines 1934–1946 (which checks the retry's output and returns None on further failure) is already correct fail-closed behavior and should NOT be modified. Informed retry is a one-shot recovery aid; persistent malformed output after one informed retry correctly stops the ticker chain per plan §2 failure policy. The first-call site at lines 1883–1894 also does NOT need `prior_validation_errors` — the default `None` is correct for the first attempt.

### 6.7 SKILL.md updates (key paragraphs)

In the "Global observations" section of `.claude/skills/earnings-learner/SKILL.md`, replace the current "0-3 entries. Each: `{scope, scope_key, lesson}`" paragraph with:

> **Global observations — 0–3 entries per attribution.**
>
> Each entry has exactly `scope`, `lesson` (1–2 sentences), and the scope-specific routing field below. **Do NOT emit `scope_key` — the field is removed; the validator rejects it.**
>
> - **`scope="sector"`** → REQUIRED `target_sector` with value from this canonical 11-value enum: `Technology`, `Healthcare`, `ConsumerCyclical`, `Industrials`, `FinancialServices`, `ConsumerDefensive`, `RealEstate`, `Energy`, `BasicMaterials`, `CommunicationServices`, `Utilities`. Do NOT include `related_tickers` or `scope_key`.
>
> - **`scope="macro"`** → include neither `target_sector`, `related_tickers`, nor `scope_key`.
>
> - **`scope="cross_ticker"`** → REQUIRED `related_tickers` as a non-empty list of uppercase ticker symbols (1–5 letters each, max 8 total, no duplicates). Do NOT include `target_sector` or `scope_key`.
>
> **Scope choice rule (mandatory):**
> - Use `cross_ticker` ONLY when the lesson is about specific named tickers. The lesson will only flow to those tickers' future predictions.
> - Use `sector` when the lesson generalizes across a whole sector (any company in `target_sector` will receive it).
> - Use `macro` for regime-wide observations (every future prediction receives it).
> - Sector-generalizable lessons written as `cross_ticker` are under-routed; prefer `sector` scope for broad lessons.

**Shape-only placeholder examples (amendment 2026-04-17)** — use abstract placeholders, NOT concrete content. LLMs exhibit strong content-anchor bias when shown specific example lessons: a concrete `"trade-tension regimes"` example primes the learner to find trade-tension framings in the current quarter even when none exist; a `["ROST", "BURL"]` pair biases peer selection; `"X dominates Y in attribution weight"` becomes a reusable phrasing template. Given we have NO escape hatch and validator semantics cannot catch template overfit, the examples must minimize content priming while preserving shape signal.

Concrete example content is explicitly rejected in Appendix C. The shape-placeholder form is:

```json
{
  "scope": "sector",
  "target_sector": "<one of the 11 canonical values listed above>",
  "lesson": "<1-2 sentences describing a causal mechanism observed in THIS quarter that plausibly generalizes to peers in target_sector; must be grounded in cited evidence, not boilerplate>"
}

{
  "scope": "cross_ticker",
  "related_tickers": ["<TICKER_A>", "<TICKER_B>"],
  "lesson": "<1-2 sentences explaining why THIS quarter's result ties these specific tickers together; the lesson should NOT apply to unrelated tickers — if it does, choose scope=sector instead>"
}

{
  "scope": "macro",
  "lesson": "<1-2 sentences; a regime-level observation that genuinely applies across sectors and is evidenced in THIS quarter's data, not a generic market truism>"
}
```

Front these with an explicit anti-anchor sentence: *"Shape examples — field layout ONLY. Do NOT copy the placeholder phrasings. Every `lesson` string must be generated from THIS quarter's specific evidence."* The placeholders are **self-describing** (they describe what content belongs in each slot rather than showing it), which preserves length/tone/specificity cues without exposing copyable content.

**Edge-case risk**: LLMs occasionally emit placeholder tokens like `<TICKER_A>` verbatim. If that happens, the validator's `_ok_ticker` check rejects them (underscore/bracket chars fail `.isalpha()`), the informed-retry (H2) fires with the exact error, and the second attempt corrects. Shape reliability thus stays high even in this failure mode.

**NOTE (consistency invariant)**: the 11-value enum in this SKILL.md MUST match `config/canonical_sectors.py::CANONICAL_SECTORS` exactly. The pre-commit test `test_canonical_sectors_consistency.py` (see §7.5) asserts both (a) the module matches the live Neo4j distinct-sector set and (b) SKILL.md's prose list mentions every value in the module. Any Neo4j sector change therefore requires updating both files in the same commit; CI catches drift on either side.

---

## 7. Test matrix

### 7.1 Validator tests — `scripts/earnings/test_validate_attribution.py` (NEW)

| # | Test | Expected |
|---|---|---|
| V1 | Full valid attribution with zero global_observations | no errors |
| V2 | `cross_ticker` with `related_tickers=["ROST"]` | no errors |
| V3 | `cross_ticker` with `related_tickers=[]` | error naming `related_tickers` |
| V4 | `cross_ticker` missing `related_tickers` field | error |
| V5 | `cross_ticker` with `related_tickers=["rost"]` (lowercase) | error |
| V6 | `cross_ticker` with `related_tickers=["TOOLONG"]` (7 chars) | error |
| V7 | `cross_ticker` with `related_tickers=["ROST","ROST"]` (duplicates) | error |
| V8 | `cross_ticker` with 9 related_tickers | error (cap=8) |
| V9 | `cross_ticker` with `target_sector="Technology"` present | error (must not have target_sector) |
| V10 | `sector` with `target_sector="Technology"` | no errors |
| V11 | `sector` with `target_sector="semiconductors"` (non-canonical) | error |
| V12 | `sector` with `target_sector` missing | error |
| V13 | `sector` with `related_tickers=["AAPL"]` present | error |
| V14 | `macro` with neither field | no errors |
| V15 | `macro` with `related_tickers=["AAPL"]` | error |
| V16 | `macro` with `target_sector="Technology"` | error |
| V17 | Required non-global fields missing (evidence_ledger etc.) | error (sanity check existing rules still fire) |
| V18 | Unknown scope value `"foo"` | error from existing `_VALID_SCOPES` check |
| V19 | Any scope with `scope_key="anything"` present | error (field removed; validator rejects across all scopes) |
| V20 | `cross_ticker` `related_tickers=["ROST","ROST"]` — duplicates | error (validator is dedupe authority; writer does NOT dedupe) |

### 7.2 Writer tests — extend `test_learning_context.py`

| # | Test | Expected |
|---|---|---|
| W1 | `append_global_lessons` for ticker with valid Neo4j sector (mocked) | entry has `source_sector` populated |
| W2 | `append_global_lessons` for ticker whose lookup returns None | `source_sector=None`, WARNING emitted |
| W3 | `related_tickers` and `target_sector` pass through untouched | stored fields equal input |
| W4 | Concurrent writes (two threads, different tickers) | both entries present, fcntl-protected, no corruption |
| W5 | Atomic write crash mid-write (force exception after temp file) | temp file cleaned up, `global.json` unchanged |
| W6 | `append_global_lessons` called twice with the same `(ticker, quarter_label)` | second call REPLACES prior entries for that key, not duplicates (upsert-by-source-key) |
| W7 | `append_ticker_lesson` called twice with the same `quarter_label` | second call REPLACES the prior entry; `lessons[]` contains exactly one entry for that quarter |
| W8 | `append_global_lessons` receives observation with `scope_key` field (learner error past validator) | writer does NOT pass it through (field dropped at enrichment time) |

### 7.3 Reader tests — rewrite `test_learning_context.py`

| # | Test | Expected |
|---|---|---|
| R1 | Empty `global.json` | both lessons arrays empty |
| R2 | File absent | both empty |
| R3 | One sector entry with matching `target_sector` | included |
| R4 | One sector entry with non-matching `target_sector` | excluded; counter `sector_mismatch=1` |
| R5 | Sector entry with current sector normalized (e.g., "technology" current, "Technology" target) | included |
| R6 | Sector entry lacking `target_sector` (legacy) | excluded; counter `legacy_schema=1` |
| R7 | Macro entry | always included |
| R8 | Cross-ticker entry with `related_tickers=["AAPL"]`, current ticker AAPL | included |
| R9 | Cross-ticker entry with `related_tickers=["MSFT"]`, current ticker AAPL | excluded; counter `cross_ticker_not_listed=1` |
| R10 | Cross-ticker entry lacking `related_tickers` (legacy) | excluded; counter `cross_ticker_missing_related=1` |
| R11 | 10 sector entries all matching | capped at 4, newest-first |
| R12 | 10 cross_ticker all matching | capped at 2 |
| R13 | Two entries identical lesson text | deduped to 1 |
| R14 | Unknown scope value entry | excluded; counter `unknown_scope=1` |
| R15 | Observability log emitted with exact field names, even when `global.json` absent | substring-asserted for each of the 6 counter keys + 3 included counts (no regex) |

### 7.4 Integration tests

| # | Test | Expected |
|---|---|---|
| I1 | Full `run_learner_for_quarter` with mocked SDK producing valid output | `global.json` has entries with all new fields populated |
| I2 | Same, but mocked output has cross_ticker without `related_tickers` | validator rejects, result.json deleted, retry triggered, re-fails → ticker chain stops per §2 failure policy |
| I3 | Predictor bundle render end-to-end with real post-fix `global.json` | Section 10 contains three correctly-labeled sub-sections |
| I4 | PreToolUse hook round-trip with malformed cross_ticker result.json content | hook blocks with reason containing `"related_tickers"` |
| I5 | `build_prediction_bundle` for a ticker with `8k_packet.sector=None` | sector populated via `_lookup_company_sector` fallback |
| I6 | Observability log at INFO level after one learner call | matches pattern with all counter names |
| I7 | Corrupted `global.json` on disk (force `json.JSONDecodeError`) during read | `log.error` emitted; predictor bundle builds with empty `global_lessons`; no crash |
| I8 | Unreadable `global.json` on disk (force `OSError`) during read | `log.error` emitted; predictor bundle builds with empty `global_lessons`; no crash |
| I9 | Derived-write recovery path re-runs an already-processed quarter | upsert fires — no duplicate entries in `global.json` or `ticker.json` after second run |
| I10 | **H2 acceptance gate** — informed retry: mocked SDK returns malformed output on attempt 1 (e.g., `cross_ticker` entry without `related_tickers`), then well-formed output on attempt 2 after receiving validation errors in the retry prompt | retry succeeds; final `attribution/result.json` validates; derived `global.json` / `ticker.json` contain the expected new-schema entry; log shows `"Retrying learner ... (1 retry, feeding N validation errors back)"` |

### 7.5 Canonical-sector consistency tests — `scripts/earnings/test_canonical_sectors_consistency.py` (NEW)

These tests enforce that the hardcoded enum, the live Neo4j set, AND the SKILL.md prose list stay aligned.

| # | Test | Expected |
|---|---|---|
| CS1 | `CANONICAL_SECTORS == {live Neo4j distinct-sector set}` | equal; test fails loudly with symmetric-difference breakdown if not |
| CS2 | SKILL.md prose mentions every value in `CANONICAL_SECTORS` | every label present; missing list reported on failure |
| CS3 | `CANONICAL_SECTORS` is frozen (no duplicates, non-empty, all str, no whitespace issues) | sanity check |

**Implementation sketch:**
```python
from config.canonical_sectors import CANONICAL_SECTORS
from scripts.earnings.utils import neo4j_session
from pathlib import Path

def test_canonical_sectors_match_neo4j():
    # Mirror the runtime coalesce logic exactly — _lookup_company_sector uses
    # coalesce(c.sector, sec.name), so the test must compute the same set or
    # drift between Industry-only-sector tickers and property-only tickers
    # could go undetected.
    with neo4j_session() as (s, err):
        assert not err, f"Neo4j unavailable: {err}"
        rows = s.run("""
            MATCH (c:Company)
            OPTIONAL MATCH (c)-[:BELONGS_TO]->(:Industry)-[:BELONGS_TO]->(sec:Sector)
            WITH coalesce(c.sector, sec.name) AS sector
            WHERE sector IS NOT NULL
            RETURN DISTINCT sector
        """).data()
        neo4j_set = {r["sector"] for r in rows}
    assert neo4j_set == CANONICAL_SECTORS, (
        f"Neo4j/enum drift detected.\n"
        f"  In Neo4j but not in CANONICAL_SECTORS: {neo4j_set - CANONICAL_SECTORS}\n"
        f"  In CANONICAL_SECTORS but not in Neo4j: {CANONICAL_SECTORS - neo4j_set}\n"
        f"Action: update config/canonical_sectors.py AND the prose enum in "
        f".claude/skills/earnings-learner/SKILL.md in the same commit."
    )

def test_skill_md_lists_all_canonical_sectors():
    skill = Path(".claude/skills/earnings-learner/SKILL.md").read_text(encoding="utf-8")
    missing = sorted(s for s in CANONICAL_SECTORS if s not in skill)
    assert not missing, (
        f"SKILL.md prose enum is missing canonical sectors: {missing}\n"
        f"Action: update the sector-enum prose paragraph in earnings-learner/SKILL.md."
    )
```

---

## 8. Rollout — single atomic commit

### 8.1 Pre-commit checklist

- [ ] Canonical sector enum in SKILL.md matches §3's 11 values exactly.
- [ ] `_lookup_company_sector` still returns expected values for AVGO, NVDA, BURL, ROST (quick manual Neo4j call).
- [ ] **All tests in §7 green** on the project venv, including the NEW consistency tests:
  ```bash
  venv/bin/python scripts/earnings/test_validate_attribution.py          && \
  venv/bin/python scripts/earnings/test_learning_context.py              && \
  venv/bin/python scripts/earnings/test_canonical_sectors_consistency.py
  ```
- [ ] `venv/bin/python -m py_compile` clean for every modified file, including `.claude/hooks/validate_attribution_output.py` and `config/canonical_sectors.py`.
- [ ] Grep confirms no remaining references to `_extract_scope_key_tickers`, `_cross_ticker_matches`, `scope_key` in code blocks of the plan, or `sector_missing_target`.
- [ ] Grep confirms no `import re` or `re\.` in the learning-context code path (validator + orchestrator) — zero regex invariant.

### 8.2 Commit contents

Single commit titled e.g. `feat(learner): structured routing for global lessons (cross_ticker + sector)`. The commit MUST contain:

- **NEW** `config/canonical_sectors.py` — hardcoded `CANONICAL_SECTORS` frozenset (§3.1).
- **MODIFIED** `scripts/earnings/validate_attribution.py` — validator additions (§6.1).
- **MODIFIED** `scripts/earnings/earnings_orchestrator.py` — writer upserts (§6.2), reader rewrite (§6.3), renderer split (§6.4), codex deletions (§6.5), informed-retry signature changes (§6.6), observability log, anti-poisoning sector cache (§3.2).
- **MODIFIED** `.claude/hooks/validate_attribution_output.py` — `sys.path.insert(0, project_dir)` added before existing insert (§5 row 3).
- **MODIFIED** `.claude/skills/earnings-learner/SKILL.md` — new schema, canonical enum, worked examples (§6.7).
- **MODIFIED** `.claude/plans/learner.md` — §8 + §9 synced with this plan.
- **NEW** `scripts/earnings/test_validate_attribution.py` — V1–V20 (§7.1).
- **REWRITTEN** `scripts/earnings/test_learning_context.py` — W1–W8, R1–R15, I1–I10 (§7.2–§7.4). I10 is the H2 acceptance gate (informed retry round-trip); commit is incomplete without it.
- **NEW** `scripts/earnings/test_canonical_sectors_consistency.py` — CS1–CS3 (§7.5).

Commit body should reference this plan file.

### 8.3 Post-commit operator steps (NOT in the commit) — SMOKE-BEFORE-WIPE order

**Rationale for ordering**: the smoke test proves the NEW pipeline (validator + informed retry + writer + reader) works against REAL data before any destructive operation. If smoke test fails, iterate SKILL.md without having destroyed anything. Only after smoke test passes do we wipe.

```bash
# ── STEP 1: Smoke test the new pipeline on 2–3 quarters BEFORE wiping ──
# These runs exercise:
#   - derived-write recovery hitting an old-schema attribution/result.json
#   - validator rejecting old schema → delete → learner re-runs with new schema
#   - informed retry (H2) if the learner's first new-schema attempt is imperfect
#   - upsert in append_global_lessons and append_ticker_lesson (idempotency)
#   - reader filtering mixed old+new schema (legacy_schema counter fires on old)
python3 scripts/earnings/earnings_orchestrator.py AVGO 0001730168-23-000053 --save --predict --learn
python3 scripts/earnings/earnings_orchestrator.py NVDA <accession> --save --predict --learn
python3 scripts/earnings/earnings_orchestrator.py BURL <accession> --save --predict --learn

# ── STEP 2: Inspect the smoke-test output ──
# For each smoke-tested quarter's attribution/result.json, confirm:
#   - Any cross_ticker observations have related_tickers populated (non-empty, UPPER, 1–5 letters)
#   - Any sector observations have target_sector from the canonical 11-value enum
#   - NO scope_key field anywhere
#   - Validator logged zero errors; if retry fired, it succeeded on attempt 2
# For global.json:
jq '.entries[] | select(.source_ticker=="AVGO" and .quarter_label=="Q1_FY2023")
    | {scope, related_tickers, target_sector, source_sector}' \
   earnings-analysis/learnings/global.json

# Smoke-test GATE: if any smoke quarter failed validation even after informed
# retry, DO NOT proceed to wipe. Iterate SKILL.md and re-run this step.

# ── STEP 3: Backup + wipe derived data (only after smoke passes) ──
# SAFETY CHECK: confirm the wipe path is not inside the Obsidian symlink tree
# managed by obsidian_thinking.md. earnings-analysis/learnings/ must be a
# real dir, NOT a symlink; otherwise the rm could nuke upstream vault content.
[ -L earnings-analysis/learnings ]                && { echo "ABORT: learnings/ is a symlink"; exit 1; }
[ -L earnings-analysis/learnings/global.json ]    && { echo "ABORT: global.json is a symlink"; exit 1; }
[ -L earnings-analysis/learnings/ticker ]         && { echo "ABORT: ticker/ is a symlink"; exit 1; }

cp -r earnings-analysis/learnings earnings-analysis/learnings.backup.$(date +%s)
rm earnings-analysis/learnings/global.json
rm earnings-analysis/learnings/ticker/*.json

# ── STEP 4: Verify empty state ──
ls earnings-analysis/learnings/ticker/      # should be empty
[ ! -f earnings-analysis/learnings/global.json ] && echo "global.json absent ✓"

# ── STEP 5: Full 15-quarter re-run chronologically per ticker ──
# (AVGO Q1→Q5, NVDA Q1→Q5, BURL Q1→Q5)
# The smoke-tested quarters re-run cleanly because their ticker.json/global.json
# entries were wiped in Step 3.

# ── STEP 6: Post-completion verification ──
jq '.entries[] | select(.scope=="cross_ticker") | {related_tickers, source_sector}' \
   earnings-analysis/learnings/global.json
jq '.entries[] | select(.scope=="sector") | {target_sector, source_sector}' \
   earnings-analysis/learnings/global.json
# Confirm scope_key has been fully purged from the rebuilt data:
! jq '.entries[] | select(has("scope_key"))' earnings-analysis/learnings/global.json | grep -q .

# ── STEP 7: Grep logs for one learning_context line per quarter re-run ──
#   (should show non-zero included counts on later-in-chronology quarters)
```

### 8.4 Operational gap caveat (user-approved)

Between STEP 3 (wipe) and completion of STEP 5 (~2–3 hours of sequential re-runs), `global.json` is progressively populated from empty. Predictor runs during this window see reduced/no global lessons **by design** per the user's "starting anew" directive. This is clean-slate behavior, NOT a regression. If zero gap is ever required, the fallback is to implement dual-read mode (reader accepts both old and new schema), but that is EXPLICITLY not in this plan.

**Gate enforcement**: STEP 3 is the destructive step. STEP 1 is the validating step. The ordering (validate → destroy → rebuild) is mandatory. Skipping STEP 1 forfeits the informed-retry safety net and violates the "must be perfect in first go" constraint that rules out an escape hatch.

---

## 9. Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Learner first-write under new SKILL.md omits `related_tickers` or `target_sector` → PreToolUse hook blocks every learner write → ticker chain stops at every quarter | Low | High if realized | **NO escape hatch** (amendment 2026-04-17 — runs unmonitored; any silent-permissive mode is ruled out). Three layers of compensating hardening: **(H1)** pre-commit smoke test is a MANDATORY GATE in §8.1 — must pass 2–3 quarters across different tickers BEFORE the wipe is performed; **(H2)** validation errors are fed back into the retry prompt so the 1-retry path is informed rather than blind (§6.6); **(H3)** validator error messages include `difflib`-based "did you mean" suggestions for `target_sector` and `related_tickers` (§6.1). Combined, these push first-attempt correctness + single-retry recovery to near-100%; any persistent failure is loud (ticker chain stops + log.error), NEVER silent. |
| R2 | Legacy `attribution/result.json` files with old-schema global_observations fail validation on re-run | Certain for 15 quarters | Low (time-bounded) | Derived-write recovery deletes invalid result.json and triggers learner re-run. Accepted cost: 15 re-runs, ~2–3h total, $0 (OAuth subscription). |
| R3 | `_lookup_company_sector` returns None for a current-run ticker (out-of-universe or bad Neo4j state) | Low (universe is 796 with zero NULLs) | Low | `source_sector=None` stamped, WARNING logged. Reader does NOT route on `source_sector` anyway, so lesson still flows correctly via `related_tickers` or `target_sector`. |
| R4 | Neo4j unreachable at append time → `source_sector=None` on every entry of the run | Low | Low | `_lookup_company_sector` returns None on any Exception. Entries still valid; `source_sector` is audit-only, not routing. Run proceeds. |
| R5 | Sector label drift in Neo4j (e.g., `Technology` renamed) | Very low | Medium | `CANONICAL_SECTORS` is hardcoded in `config/canonical_sectors.py` AND pre-commit test `test_canonical_sectors_consistency.py` queries Neo4j and fails loudly on any divergence (CS1). Mitigation is automated, not operator-dependent. Any Neo4j rename = loud pre-commit-test failure with specific remediation message → single commit updates module + SKILL.md + re-wipe if appropriate. |
| R6 | `normalize_sector` differs between write-time Neo4j value and validator enum (e.g., Unicode) | Very low | Low | Enum is ASCII-only canonical. Validator uses exact string membership. Reader uses `_normalize_sector` on both sides defensively. |
| R7 | Concurrent writer corruption of `global.json` | Low (existing fcntl.flock) | High | Unchanged from today. Atomic write + flock verified by W4. |
| R8 | Renderer token budget increase from sub-section headings | Negligible | Low | ~20 tokens extra. Predictor prompt tolerates easily. |
| R9 | Predictor SKILL.md assumes specific rendered-bundle heading strings | None (confirmed) | n/a | Verified: `/earnings-prediction/SKILL.md` reads bundle at `BUNDLE_PATH` as free text. No heading literals referenced. |
| R10 | A future regression reintroduces silent drop | Low | Medium | Observability log R15 test asserts all six counter names appear. Any filter change without corresponding test update fails CI. |
| R11 | Learner's judgment on scope=sector vs cross_ticker is wrong in a specific case | Medium | Low (soft failure) | Under-routed lesson is recoverable next quarter. Over-routed is not possible (no same-sector fallback). SKILL.md rule is explicit. |
| R12 | Backups accumulate under `.backup.*` | Certain over time | Negligible | Add `learnings.backup.*` to `.gitignore`. Operator can `rm -rf` at will. |
| R13 | Infrastructure errors (corrupt/unreadable `global.json` or `ticker.json`) silently suppressed | Low | Medium | Amendment 2026-04-17 adds `log.error` on every `except (json.JSONDecodeError, OSError)` path in the reader. Predictor still builds (defensive) but operator sees the incident in logs. |
| R14 | Derived-write recovery or accidental re-run inflates `global.json` / `ticker.json` with duplicate entries | Medium | Low (reader dedupes anyway, but file grows) | Amendment 2026-04-17 converts both append functions to upsert-by-source-key (§6.2). First write unchanged; re-runs replace in place. Tests W6, W7 verify. |

---

## 10. Out of scope / future work

This plan solves **global-lessons routing and storage correctness**. It does NOT address broader questions about whether the learner-predictor loop is net-helpful on prediction quality.

**Actionable TODO backlog moved to `learner.md` "Outstanding Follow-Ups / TODO" section (top of file)** — that location is the single canonical source. Items such as the labeled-lesson-consumption mitigation (T1), `guidance_history.series` fix (T2), `build_8k_packet.sector` source fix (T3), fresh A/B (T4), obsidian_thinking.md rename coordination (T5), CI workflow (T7), and every other follow-up originally listed here are now tracked under numbered tiers (🔴 Next up / 🟡 Backlog / 🗑️ Declined) in `learner.md`.

Items DECLINED by this plan (documented here for local-context reference, also in Appendix C): dual-read migration mode, same-sector fallback for cross_ticker, schema version bump for `global_lessons.v1`, concrete worked examples in SKILL.md, keeping `scope_key` as vestigial display field.

For a full concern-by-concern historical audit (C16–C29), see §12.

---

## 11. Validation checklist for the user (pre-implementation sign-off)

Before greenlighting implementation, confirm:

- [ ] The single-commit atomicity is understood: schema, validator, writer, reader, renderer, SKILL.md, plan doc, tests all in one commit.
- [ ] The 2–3h operational gap during post-commit re-run is acceptable.
- [ ] Codex's revert procedure (§1.4) is understood as a safety net.
- [ ] The canonical 11-value sector enum in §3 will be frozen verbatim in the validator.
- [ ] The "no source_sector fallback for cross_ticker" design is understood — same-sector broadcasting is deliberately not a routing path.
- [ ] The "no dual-read mode" design is understood — legacy entries are transparently dropped post-wipe.
- [ ] **No escape hatch** — system is designed for unmonitored execution; compensating hardening is (H1) mandatory pre-commit smoke-test gate, (H2) informed retry with validation errors fed back into prompt, (H3) `difflib` suggestions in validator errors. Failure mode is fail-closed and loud, never silent.
- [ ] Pre-commit checklist (§8.1) and post-commit operator steps (§8.3) are actionable.

---

## Appendix A — Neo4j sector distribution (verified 2026-04-17)

```
Technology              162
Healthcare              145
ConsumerCyclical        121
Industrials             110
FinancialServices        54
ConsumerDefensive        44
RealEstate               36
Energy                   35
BasicMaterials           34
CommunicationServices    30
Utilities                25
                    ─────
TOTAL                   796 (zero NULLs within universe)
```

## Appendix B — Lessons dropped under the pre-codex bug (real evidence)

From `earnings-analysis/Companies/*/events/*/attribution/result.json`, never reached any predictor via the global channel until codex's stopgap:

- AVGO Q3_FY2023 `cross_ticker:conglomerate_earnings` — "veto-condition pattern for diversified issuers"
- AVGO Q4_FY2023 `cross_ticker:*` — VMware-AI-rerating cross-reads
- AVGO Q1_FY2024 `cross_ticker:*` — sub-segment composition-shift template
- BURL Q1_FY2025 `cross_ticker:ROST_BURL` — "quality match prerequisite for peer analog validity"
- BURL Q2_FY2025 `cross_ticker:sequential_beat_quality` — "doubt resolution premium" pattern
- BURL Q3_FY2025 `cross_ticker:margin_vs_sales_tradeoff_disclosure`
- BURL Q4_FY2025 `cross_ticker:*` — call-as-separate-catalyst pattern
- NVDA (multiple) — AI infrastructure cross-reads

Plus every sector-scope entry written with non-canonical `scope_key` (`semiconductors`, `off_price_retail`, `post_rally_earnings`, …) — silently dropped by the raw-equality filter. After this plan lands, all similar future entries route correctly.

## Appendix C — Decision log (considered and explicitly rejected)

| Alternative | Why rejected |
|---|---|
| Keep codex's regex-based cross_ticker matcher | False-positive hazard on English-word-shaped scope_keys (`LOW`, `ONE`, `AI`). Ambiguous semantics. Harder to audit. |
| Same-sector fallback for cross_ticker (route via `source_sector == current_sector`) | Reintroduces the template-overfit-at-sector-scale failure mode. If broad applicability is needed, `scope=sector` exists. ChatGPT simulation confirms ~162 Technology tickers would see every AVGO lesson under this policy. |
| Fix `builder_adapters.build_8k_packet` to populate sector, then drop `_lookup_company_sector` | Out of scope; legacy builder is brittle; unknown blast radius. Deferred to a separate PR. |
| Dual-read mode (accept old + new schema in the reader during transition) | User approved clean slate. Adds ~20 lines and a future cleanup task. Not worth the complexity for a 2–3h gap. |
| Schema version bump (`global_lessons.v1` → `v2`) | Only one reader. No external consumers. Additive fields don't require a bump. |
| Use `Industry` level instead of `Sector` for `target_sector` routing | Finer granularity is attractive but requires a larger enum and a new Neo4j query. Not required for current calibration. Future work. |
| Separate validator LLM run to label lessons ex-ante | Out of scope; belongs in `learner.md §11` mitigation. |
| Keep `scope_key` as the sector routing field but add a normalize+enum check | Still conflates display and routing. Asymmetric with cross_ticker. `target_sector` separation is strictly cleaner. |
| Keep `scope_key` as a vestigial display-only field | Added amendment 2026-04-17: it earns nothing (not routed, not deduped, not filtered, redundant with `lesson`), ~30 tokens of learner fluff per entry. Strictly better to delete. |
| Writer silently dedupes `related_tickers` | Added amendment 2026-04-17: hides authoring errors. Validator rejection + learner retry forces clean output. Writer is pure pass-through. |
| Fetch `CANONICAL_SECTORS` from Neo4j at validate-time | Breaks fail-closed design of the stdlib-only PreToolUse hook. Adds Neo4j failure mode to every learner write. pre-commit consistency test achieves same drift-protection without runtime coupling. |
| Pure-append without upsert in derived-write functions | Creates duplicate entries on any re-run; reader dedupe masks the correctness impact but files grow unbounded. Upsert-by-source-key is ~6 lines and fully eliminates the drift. |
| Concrete worked examples in SKILL.md (e.g., `"During elevated trade-tension regimes..."`) | Added amendment 2026-04-17 (post initial implementation): LLMs show strong content-anchor bias on concrete examples — they copy noun phrases, peer-ticker pairs, and phrasing templates into unrelated-quarter outputs. Compounding factor: template overfit is the specific failure mode the whole learner architecture tries to engineer out, and we have NO escape hatch. Shape-only placeholders with an explicit anti-anchor instruction (§6.7) preserve length/structure cues without exposing copyable content. Validator failure mode on routing fields (LLM emits `<TICKER_A>` verbatim) is cleanly handled by H2 informed retry. Strictly better trade-off. **Residual risk (honest caveat)**: the validator enforces `lesson` as a string but NOT semantically — an LLM that copies `"<1-2 sentences describing..."` verbatim into a `lesson` value would pass schema validation. The failure mode is rare in practice (LLMs read `<...>` as instructions, not literal text) but not zero; it is caught at the §8.3 STEP 2 smoke-inspection gate where the operator eyeballs the lesson content before the wipe. |

---

## 12. Known concerns OUTSIDE the scope of this plan — historical audit

> **NOTE**: the ACTIONABLE backlog moved to `learner.md` "Outstanding Follow-Ups / TODO" (top of file). This section is preserved as the historical concern audit that informed the priority tiers in that TODO list — i.e., this is the "why" behind T1–T19 in `learner.md`. Individual concerns below map directly to those Ts (T-prefix cross-refs in the right-hand column where applicable).

This plan is narrowly scoped to **routing/storage correctness for global lessons**. A broader earlier review raised numerous concerns about the learner's actual utility for prediction. Many of those are NOT addressed here. This section tracks them explicitly so future readers know what remains open.

**Addressed directly by this plan** (no further action needed here):

| Concern | Location |
|---|---|
| `cross_ticker` silent drop | §2.1, §4.3, §6.3 |
| `sector` scope silent drop via raw-equality | §2.2, §6.1, §6.3 |
| `8k_packet.sector = None` on all bundles | §2.3; fallback kept |
| No observability on filter behavior | §4.5, §6.3 (log line with include/exclude counters) |
| `scope_key` doing double duty | Removed entirely; §4.1, §6.1 (validator rejects), §6.2, §6.4, §6.7 |
| Misleading renderer heading | §6.4 (three sub-sections) |
| Validator duplicate-field ambiguity | §6.1 (validator authoritative; writer pass-through) |
| Silent `except: pass` on read failures | §6.3 (log.error on both paths) |
| Duplicate-append drift on re-runs | §6.2 (upsert-by-source-key) |
| Canonical-sector source-of-truth | §3.1 (module + CS1/CS2 pre-commit tests) |

**Deferred to a separate PR** (acknowledged here; not acted on):

| Concern | Rationale for deferring |
|---|---|
| Template overfit — predictor over-applies prior lesson without mechanism-check against current bundle | Requires §11 labeled-lesson-consumption mitigation in `learner.md`. Separate predictor-side change. Independent of routing. |
| `guidance_history.series = []` on all 15 calibration quarters | Higher-EV independent PR. Likely more impactful on prediction quality than any lesson-routing change. |
| `build_8k_packet.sector` not populated at source | Legacy builder; separate PR. Until then, fallback is load-bearing. |
| Industry-level routing (finer than sector) | Deferred until empirical need. |
| Predictor's side of labeled consumption | Part of the §11 mitigation; learner-edits does not touch predictor logic. |

**NOT mentioned at all in the earlier plan state** — fold in as a follow-up backlog (cross-referenced as C16–C29 from the session concern audit):

| ID | Concern | Recommended next step |
|---|---|---|
| C16 | Confidence-drift monitoring (BURL Q3_25: WITH=62 vs WITHOUT=58 on wrong call) | Offline audit script over `prediction_result.v1` files; not blocking. |
| C17 | Hindsight contamination — learner sees actual return and constructs causal narratives fitting outcome | Structural; consider separate label-only LLM (see §11 "alternative if labels dishonest"). |
| C18 | SKILL.md frontmatter vs runtime drift (frontmatter is documentation-only) | One-line note in SKILL.md; trivial follow-up. |
| C19 | A/B methodology confound (BURL on Opus 4.6/high vs 4.7/xhigh for AVGO/NVDA) | Phase 8.3 re-runs will use current prod config, which incidentally fixes this; call out in the re-run plan. |
| C20 | `data_lessons` conflates "fetch X" vs "weight X more" | Learner-output schema split; separate PR. |
| C21 | `model_version` override could mask silent model fallback | Already mitigated by `_assert_claude_code_oauth_ready` + `cli_path=` pin; low priority hardening. |
| C22 | `magnitude_error_pct` semantics for `no_call` | Minor validator tightening; separate PR. |
| C23 | Lesson refinement vs replacement — append-only ticker.json preserves old wrong lessons | Predictor SKILL.md instruction to prefer newer corrective lessons (adjacent to §11). |
| C24 | Predictor doesn't weight corrective lessons higher | Same as C23. |
| C25 | PIT tier-3 (`invocation_time`) non-stationarity on most-recent quarter | Design tradeoff in `learner.md §3`; may need revisit. |
| C26 | Lesson dominance in prompt budget (Section 10 placement, recency weight) | Indirect mitigation via caps; active control is future work. |
| C27 | Template-overfit rate monitoring | Offline metric after §11 lands. |
| C28 | Self-correction latency (always 1 quarter; no structural immunity) | Symptom of C9; mitigation is §11. |
| C29 | Thinking-token capture for audit of §11 label honesty | `include_partial_messages=True` in SDK options when §11 is being audited. |

**Honest framing**: after this plan lands, routing/storage correctness is solved and observable. Whether the learner ultimately improves prediction quality remains an open empirical question gated on §11 (template overfit mitigation), the guidance-history fix, and a fresh A/B harness. None of those are in this PR.

---

**End of plan.**

**Author**: Claude (session 2026-04-17), synthesizing verified findings from direct code/artifact inspection and incorporating ChatGPT-codex critiques on cross_ticker routing design, sector-structured routing, silent-failure paths in infrastructure reads, duplicate-dedupe authority, and vestigial-field removal. Every decision traceable to evidence in the repo at commit `aa3aaaa` or in the session transcript. Amendment set applied 2026-04-17 covers: `scope_key` removal, `config/canonical_sectors.py` + pre-commit consistency test, read-failure observability, validator-only duplicate authority, upsert-by-source-key idempotency, and §12 concern-tracking.


---

# Appendix B — Labeled Lesson Consumption / T1 (formerly `labeled-lesson-consumption.md`)

> **Status**: SHIPPED in commit `8a15862` on 2026-04-19. Merged into this file same day (was `.claude/plans/labeled-lesson-consumption.md`).
> Section numbering below is SELF-CONTAINED to this appendix — do not confuse with learner.md §N or Appendix A §N.


**Created**: 2026-04-19 (rev 3)
**Status**: DESIGN — production-grade, zero-fat, ready for implementation
**Scope**: Predictor-side. Make `key_drivers[]` lesson citations **structurally enforced** by the validator; the `analysis` free-text field retains a narrow, explicitly acknowledged paraphrase residual (§2.2). Not prompt-governed for citations; honestly scoped for analysis.

**Revisions history**:
- Rev 1 (earlier 2026-04-19) — introduced `lesson_labels[]`; citation discipline was prompt-only → insufficient.
- Rev 2 (earlier 2026-04-19) — added `cites_lesson_indices[]` + two-layer validation; 4 residual gaps identified on audit.
- **Rev 3 (THIS FILE)** — drops hook (pure fat), restores bundle_evidence sentinel check (rev-1 regression), collapses extractor into renderer (zero drift surface), adds analysis-field substring floor, pre-enumerates all call sites, anchors to structured `bundle["learning_context"]` not prose render.

**Parent plan**: `.claude/plans/learner.md` §13 Phase 4. This file is the authoritative spec.

**Prerequisites** (from `learner.md`'s "🔴 Next up" backlog):
1. ✅ T1.5a + T1.5b (PIT correctness) — commits `1b79614`, `fe0326a`
2. ✅ T3 (`8k_packet.sector` at source) — commit `c73599d`
3. ⏳ **Task #356** — corpus wipe + 15-quarter rerun — REQUIRED before T1 A/B is meaningful
4. ⏳ T1 (this plan)
5. ⏳ T4 — A/B evaluation on post-T1 corpus
6. ⏳ Audit script (deferred from T1; ships after ≥10 T1 quarters exist)

**NO backward compatibility.** Corpus will be wiped before T1 ships. `lesson_labels` is strictly required on every new `prediction_result.v1`. The optional `expected_lesson_texts` kwarg exists only for offline audit reads where the bundle isn't available — explicitly an offline concession, not a runtime fallback.

---

## 0. TL;DR

**Bug**: The predictor treats past lessons as soft triggers and applies them on surface keyword matches without checking whether each lesson's mechanism is present in the current bundle. AVGO Q3_FY2023 and BURL Q1_FY2025 were mis-called specifically because of this over-application.

**Fix (rev 3 — key_drivers citation structurally enforced; analysis residual explicit)**:

1. The predictor emits a `lesson_labels[]` entry for every lesson in `bundle["learning_context"]`, labeling each `confirmed` / `contradicted` / `irrelevant` with a `bundle_evidence` citation from the current quarter.
2. Every `key_drivers[i]` entry carries `cites_lesson_indices: list[int]` into `lesson_labels[]`. The validator rejects any index that does not resolve to a `confirmed` label.
3. The Python validator enforces four structural guards:
   - shape + enum + non-empty-text + bundle_evidence sentinel discipline
   - positional equality between `lesson_labels[*].lesson_text` and an orchestrator-computed expected list (no empty-list escape, no fabrication, no misordering)
   - `cites_lesson_indices` → confirmed-only enforcement
   - `analysis` field substring floor (rejects verbatim quote of any non-confirmed `lesson_text`)
4. The expected list is produced by `_render_learning_context` which now returns `(rendered_text, ordered_lesson_texts)` as a tuple. **The renderer is the single source of truth for lesson order** — the validator compares against the exact list the renderer emitted, so drift between "what LLM saw" and "what validator expects" is structurally impossible.

**No PreToolUse hook.** Python post-return validator is authoritative and runs before any **business-logic consumer** reads the result. Sidecar artifacts (`result.md`, `thinking.md`) can be generated pre-validation as diagnostic capture — acceptable and explicitly scoped in §6.1; no business-logic consumer reads them. The learner has a hook only because it has a derived-write-recovery path; the predictor has none. Asymmetry is correct, not oversight.

**Delta** (per §7 file inventory, authoritative — all numbers reconciled including import lines at non-orchestrator sites): ~164 lines of code changes across 8 source files:

| File | Lines | Contents |
|---|---:|---|
| `earnings_orchestrator.py` | +75 | validator blocks (+60), renderer tuple refactor (+8), `_normalize_lesson_text` (+4), `render_bundle_text` unpacking (+1), Site A wiring (+2) |
| `earnings-prediction/SKILL.md` | +65 | Phase 0 (+45), Output JSON example (+10), field definitions (+10) |
| `run_ab_baseline.py` | +4 | Site B wiring (3) + import (1) |
| `run_burl_ab_sequential.py` | +4 | Site C wiring (3) + import (1) |
| `run_calibration_sequential.py` | +4 | Site D wiring (3) + import (1) |
| `run_nvda_ab_sequential.py` | +4 | Site E wiring (3) + import (1) |
| `run_q3_from_existing_bundle.py` | +4 | Site F wiring (3) + import (1) |
| `.claude/plans/learner.md` | +4 | plan-doc sync |
| **Total source** | **~164** | |
| Tests (`test_validate_prediction_result.py` V1–V24 +130, `test_render_learning_context.py` R1–R4 +35) | ~165 | |
| **Grand total** | **~329** | |

**All 6 validator call sites are uniformly wired** with the `expected_lesson_texts` kwarg — no active/paused split. A/B test RUNS remain paused per user directive (2026-04-19); the A/B scripts are dormant-but-fully-wired, ready to reactivate without further code change. Total touched: 10 files. Zero fat.

**Deferred to separate PR**: audit script (~130 lines). Threshold calibration requires real T1-quarter distribution.

---

## 1. The bug (with empirical evidence)

### 1.1 Confirmed cases

**AVGO Q3_FY2023** (`Companies/AVGO/events/Q3_FY2023/learning/result.json`):
- Prior lesson (Q1): *"When a company first quantifies AI revenue, treat as narrative re-rating → long bias."*
- Q3 reality: AI was quantified in Q1 AND Q2. Q3 is the *third* disclosure — lesson's "first-time" trigger is absent.
- Predictor output: `long(40)`. Lesson applied on keyword match.
- Actual: **−5.38% SHORT**. Real signal was non-AI segment weakness.

**BURL Q1_FY2025** (`Companies/BURL/events/Q1_FY2025/learning/result.json`):
- Prior lesson (Q4): *"Compressed-spring pattern — guide-below-consensus + cautious management + clean beat → reversal rally."*
- Q1 reality: margin pressure + execution risk. "Clean beat" prerequisite absent.
- Predictor: `long(52)`.
- Actual: **−4.54% SHORT**.

### 1.2 Impact at n=15 calibration quarters

| | Correct | Rate |
|---|---|---|
| WITH lessons | 9/15 | 60% |
| WITHOUT lessons | 10/15 | 67% |
| **Delta** | **−1** | near-breakeven, asymmetric over-commitment |

### 1.3 Why prompting alone cannot fix this

SKILL.md at time of bug-observation explicitly describes lessons as "soft priors, not hard rules." Overfit still happened. LLMs are unreliable at soft meta-rules in prose. The fix must bind behavior to validator-enforced structural constraints.

---

## 2. The fix (one sentence)

Every atomic lesson in `bundle["learning_context"]` gets a `{lesson_text, label, bundle_evidence}` entry in `prediction_result.v1::lesson_labels[]` (emitted in the order the renderer emits them), every `key_drivers[i]` names the lessons it cites via `cites_lesson_indices`, and the Python validator enforces: positional equality of lesson_texts, citation-confirmed-only, bundle_evidence sentinel discipline, and an analysis-field substring floor against verbatim quotes of non-confirmed lessons.

### 2.1 Mechanism trace — AVGO Q3 after T1 ships

1. **Orchestrator** calls `_render_learning_context(bundle["learning_context"])` which returns `(rendered_text, expected_lesson_texts)`. For AVGO Q3, `expected_lesson_texts = ["<Q1 AI lesson>", "<Q2 thin-beat lesson>", ...]` in traversal order.
2. **LLM** reads `bundle.learning_context` directly from the JSON file at `BUNDLE_PATH`. Walks `ticker_lessons[*].predictor_lessons[]` then scope-ordered `global_lessons[*].lesson`. For the Q1 AI lesson: *"does Q3 bundle show FIRST AI quantification?"* → No. Emits `{lesson_text: "<verbatim>", label: "irrelevant", bundle_evidence: "AI revenue was quantified in Q1 and Q2 earnings releases; Q3 is the third consecutive disclosure."}`.
3. **LLM** decides direction from bundle evidence alone. `key_drivers = [{"driver": "Non-AI segment deceleration", ..., "cites_lesson_indices": []}, ...]`. No citation to index 0.
4. **Validator** fires:
   - Shape/enum ✓
   - `bundle_evidence != "no relevant evidence"` for `irrelevant` → OK (sentinel only rejects that string on `confirmed`/`contradicted`)
   - `lesson_labels[0].lesson_text` matches `expected_lesson_texts[0]` post-normalization ✓
   - `cites_lesson_indices` all empty or reference `confirmed` labels ✓
   - `analysis` does not contain verbatim `lesson_text` of index 0 ✓
5. **Result**: valid SHORT call. The irrelevant AI lesson is structurally barred from appearing in `key_drivers[].cites_lesson_indices`. Verbatim quotes in `analysis` (for lesson_texts ≥30 chars) are also caught by the substring floor. The residual surfaces are: (a) *paraphrased* references in `analysis` free-text (§2.2); (b) verbatim quotes of lessons <30 chars (below substring floor threshold — see §3 invariant 6).

### 2.2 Residual risk — paraphrased leak in `analysis`

**What is NOT enforced**: the LLM paraphrasing an irrelevant lesson's content into `analysis` free-text without verbatim quoting. Example: if the Q1 AI lesson text is *"first-time AI quantification drives re-rating"*, the LLM could write `analysis: "The company's re-rating prospects hinge on how investors digest this AI disclosure..."` — not a substring match but semantically citing the lesson.

**Why not fixed structurally**: catching paraphrase requires semantic comparison, which would need a second LLM call per validation — reintroduces confirmation bias and cost.

**Structural floor**: the validator rejects any `analysis` text containing the verbatim normalized `lesson_text` of a non-confirmed label. Catches the laziest leak pattern; raises the bar against rubber-stamping.

**Explicit acceptance**: this is the only prompt-governed surface in rev 3. Acknowledged, not pretended away. Detection happens offline via future audit.

---

## 3. Design invariants (MUST hold in every future change)

1. **Structural, not prose.** Labels and citation-sets are machine-readable enums/lists. Never parsed from free text.
2. **Positional integrity by construction.** `lesson_labels[i].lesson_text` corresponds to `expected_lesson_texts[i]` — same order, content-equal after whitespace normalization. Both produced by the same `_render_learning_context` call — the renderer is the single source of truth.
3. **No escape via empty.** If `expected_lesson_texts` is non-empty, `lesson_labels` must match it exactly.
4. **Citation ⇒ confirmed.** Every `key_drivers[i].cites_lesson_indices[j]` must resolve to `label == "confirmed"`.
5. **Sentinel discipline.** `bundle_evidence = "no relevant evidence"` is valid ONLY for `label == "irrelevant"`. `confirmed` and `contradicted` require specific evidence — validator rejects the sentinel for them.
6. **Analysis-field substring floor.** `analysis` must not contain the verbatim normalized `lesson_text` of any non-confirmed label **whose normalized length is ≥ 30 characters**. Shorter lessons are skipped by the substring check to prevent innocent-collision false positives on common short phrases (e.g., *"margin pressure continued"*). Real learner lessons are 80–150 chars per §1 observations; 30-char threshold is conservative and documented in §8.4 implementation.
7. **Scope is directional.** `predictor_lessons[]` + `global_lessons[].lesson` labeled. `data_lessons[]` rendered but NOT labeled (fetch/weight heuristics, not directional templates).
8. **No backward compat at runtime.** `lesson_labels` is strictly required on every new prediction. `expected_lesson_texts=None` kwarg is for offline audit only.
9. **Structured-bundle anchoring.** The LLM reads `bundle["learning_context"]` from `BUNDLE_PATH` (JSON) for label emission. The render is context for directional reasoning, not the authority on lesson text.
10. **No PreToolUse hook.** Python validator is the single validation layer. Defensive hook can be added later if derived-write recovery is introduced.

---

## 4. Schema contract — exact shape

### 4.1 Additions to `prediction_result.v1` (additive; no version bump)

```json
{
  "schema_version": "prediction_result.v1",
  "ticker": "AVGO",
  "quarter_label": "Q3_FY2023",
  "direction": "short",
  "confidence_score": 58,
  "expected_move_range_pct": [3.0, 6.0],

  "lesson_labels": [
    {
      "lesson_text": "<verbatim from bundle.learning_context>",
      "label": "irrelevant",
      "bundle_evidence": "AI revenue was quantified in Q1 and Q2 earnings releases; Q3 is the third consecutive disclosure."
    }
  ],

  "key_drivers": [
    {
      "driver": "Non-AI segment deceleration",
      "direction": "short",
      "evidence": "Infrastructure segment QoQ −4.1% per EX-99.1",
      "cites_lesson_indices": []
    },
    {
      "driver": "Thin-beat + rally-into-print",
      "direction": "short",
      "evidence": "5-day pre-print +7.2%; revenue beat 0.4%",
      "cites_lesson_indices": [1]
    }
  ],

  "data_gaps": [],
  "evidence_ledger": [ /* existing shape */ ],
  "analysis": "<free text; must not contain verbatim lesson_text of any non-confirmed label>"
}
```

### 4.2 `lesson_labels[]` — field rules

| Field | Type | Rules |
|---|---|---|
| `lesson_text` | string | Verbatim copy of the lesson string from `bundle.learning_context`. Non-empty after `.strip()`. |
| `label` | string | **Strictly** one of `"confirmed"` / `"contradicted"` / `"irrelevant"`. Lowercase, no synonyms. |
| `bundle_evidence` | string | Non-empty after `.strip()`. For `irrelevant`: `"no relevant evidence"` is allowed (sentinel). For `confirmed`/`contradicted`: must NOT be the sentinel; must be a specific citation from the current bundle. |

### 4.3 `key_drivers[i].cites_lesson_indices` — field rules

| Field | Type | Rules |
|---|---|---|
| `cites_lesson_indices` | `list[int]` | **Required** on every driver. May be empty `[]` (bundle-derived, no lesson support). Each index: `0 <= idx < len(lesson_labels)` AND `lesson_labels[idx].label == "confirmed"`. |

### 4.4 What gets labeled — scope

| Source | Labeled? |
|---|---|
| `ticker_lessons[i].predictor_lessons[]` (each string) | ✅ YES |
| `ticker_lessons[i].data_lessons[]` | ❌ NO — fetch/weight heuristics, not directional |
| `ticker_lessons[i].why` | ❌ NO — metadata |
| `ticker_lessons[i]` parent (quarter header info) | ❌ NO — metadata |
| `global_lessons[i].lesson` (scope=sector) | ✅ YES |
| `global_lessons[i].lesson` (scope=macro) | ✅ YES |
| `global_lessons[i].lesson` (scope=cross_ticker) | ✅ YES |

### 4.5 Empty / degenerate cases

| Situation | `lesson_labels` | every `cites_lesson_indices` |
|---|---|---|
| First quarter of a ticker (no prior lessons exist anywhere) | `[]` | `[]` |
| A/B baseline (learning_context intentionally blanked) | `[]` | `[]` |
| 3 ticker + 2 global lessons rendered | array of length 5 in render-order | 0–5 indices each |

---

## 5. Render contract — single source of truth

### 5.1 Current state of `_render_learning_context`

At `scripts/earnings/earnings_orchestrator.py:2485`, returns `str` (rendered text). Called from `render_bundle_text` at line 1502. Render order:

1. Ticker lessons (recency-sorted by `build_learning_context`):
   - For each ticker_lesson, emit `**{quarter_label}** — ...` header
   - For each `predictor_lessons[*]`: `  - Predictor: <text>`  ← LABELED
   - For each `data_lessons[*]`: `  - Data: <text>`  ← NOT labeled
   - `  - Why: <why>` ← NOT labeled
2. Global lessons by scope:
   - `scope == "sector"` → `- [sector:{ts}] ({src}) {lesson}`  ← LABELED
   - `scope == "macro"` → `- [macro] ({src}) {lesson}`  ← LABELED
   - `scope == "cross_ticker"` → `- [cross:{rt}] ({src}) {lesson}`  ← LABELED

### 5.2 Refactor: renderer returns tuple

**Change**: `_render_learning_context(ctx: dict) -> tuple[str, list[str]]` — returns `(rendered_text, ordered_lesson_texts)`.

**Impact**:
- Single source of truth: the same function that emits the render also emits the expected list. By construction, render order == list order. **Zero drift surface.**
- `render_bundle_text` at line 1502 unpacks: `text, _expected = _render_learning_context(learning_ctx)` — keeps the text, discards the list (its own callers don't need it yet). Signature of `render_bundle_text` unchanged.
- New callers (the validate call sites) call `_render_learning_context(bundle["learning_context"])[1]` directly to get the list.

**Why this is strictly better than rev-2's separate `_extract_expected_lesson_texts` helper**: two functions producing "the same list in the same order" is an invariant that must be maintained forever. One function producing both eliminates the invariant.

### 5.3 Whitespace normalization helper

Add module-level helper `_normalize_lesson_text` for stable positional comparison AND the analysis substring floor:

```python
def _normalize_lesson_text(s: str) -> str:
    """Whitespace-collapse + strip + case-fold for stable comparison.

    Used for (a) positional equality between LLM-emitted lesson_text and the
    renderer's expected list, and (b) the analysis-field substring floor.
    Case-folding absorbs harmless capitalization drift without weakening
    either check meaningfully — LLMs do not reliably preserve case, and an
    intentional verbatim quote survives case folding.
    """
    return " ".join((s or "").strip().split()).lower()
```

Used on both sides of the positional check and in the analysis-leak check.

### 5.4 SKILL.md order instruction

Because the LLM reads `bundle.learning_context` from JSON (§9), its emission order must match the renderer's traversal. SKILL.md instructs the order explicitly (see §8.1).

---

## 6. Validation (single layer — Python post-return)

### 6.1 Why no PreToolUse hook

The learner has `validate_learning_output.py` because the learner's derived-write recovery path (orchestrator line 1865-1889) reuses an existing `learning/result.json` if present. A malformed write caught at disk-write time prevents the recovery path from ever seeing bad data.

The **predictor has no such recovery path**. Its flow at `earnings_orchestrator.py:3284-3299`:
1. SDK call writes `result.json`
2. `finalize_prediction_result` loads + enriches + writes back; also calls `_render_and_harvest_best_effort` at line 3005 which generates `result.md` sidecar and captures `thinking.md`
3. `validate_prediction_result` runs on the loaded payload

**Honest scoping**: sidecar artifacts (`result.md`, `thinking.md`) can be generated *before* validation rejects malformed content. These are **diagnostic/viewing artifacts only** — no business-logic consumer reads them to make decisions. Downstream readers of predictions (A/B analysis, trade execution, audit tooling) all read `result.json` which is validator-gated. For failed quarters, run_ledger (#362) records the `FAILED_VALIDATION` outcome; a human reviewer can see the sidecar exists alongside that status.

So the tight claim is: **no business-logic consumer reads an unvalidated result.** Sidecar generation for failed predictions is an acceptable trade-off — the thinking capture is often MORE valuable for a failed prediction (aids post-mortem debugging). A hook would prevent this diagnostic capture for zero business-logic benefit.

If this ever becomes a concern (e.g., a new consumer reads `result.md` as an input), add a hook at that time — by delegating to `validate_prediction_result` the same way `validate_learning_output.py` delegates to `validate_attribution_result`.

### 6.2 New signature of `validate_prediction_result`

```python
def validate_prediction_result(
    payload: dict[str, Any],
    expected_ticker: str,
    expected_quarter: str,
    *,
    expected_lesson_texts: list[str] | None = None,
) -> None:
```

**Backward-compatible**: 6 existing call sites (§7.3) pass only the first 3 args today. Adding a new kwarg with `None` default does NOT break them — but without the kwarg, the positional cross-check is skipped. All NEW runtime call sites MUST pass the kwarg for the structural contract to hold. This plan wires all 6 sites; `None` remains only for offline audit use.

### 6.3 Validation order

1. Existing validations (unchanged)
2. `lesson_labels` shape + enum + non-empty strings
3. Bundle_evidence sentinel discipline (sentinel only for `irrelevant`)
4. Positional content equality (iff `expected_lesson_texts is not None`)
5. `cites_lesson_indices` shape + range + confirmed-only
6. Analysis-field substring floor (rejects verbatim quote of non-confirmed `lesson_text`)

---

## 7. File-by-file change inventory (single atomic commit)

| # | File | Action | Lines (approx) |
|---|---|---|---|
| 1 | `.claude/skills/earnings-prediction/SKILL.md` | **Modify** — add Phase 0 (+45), extend Output JSON example (+10), add field definitions (+10). | +65 |
| 2 | `scripts/earnings/earnings_orchestrator.py` — `_render_learning_context` | **Modify** — change signature to return `tuple[str, list[str]]`; append `predictor_lessons[*]` and scope-ordered `global_lessons[*].lesson` to a local list as they are emitted. | +8 / −1 |
| 3 | `scripts/earnings/earnings_orchestrator.py` — `render_bundle_text` line 1502 | **Modify** — unpack tuple: `text, _expected = _render_learning_context(learning_ctx)`; use `text`. | +1 / −1 |
| 4 | `scripts/earnings/earnings_orchestrator.py` — `_normalize_lesson_text` helper | **New** — module-level. | +4 |
| 5 | `scripts/earnings/earnings_orchestrator.py` — `validate_prediction_result` | **Modify** — add kwarg + 6 validation blocks per §6.3. | +60 |
| 6 | Caller wiring at **all 6** validate call sites (§7.3) | **Modify** — extract list, pass kwarg. Site A: 2 lines (bundle in scope). Sites B, C, D, E, F: 3 lines each (bundle-load + renderer + kwarg) + 1 import line each. | +22 (2 + 3×5 + 5 imports) |
| 7 | `.claude/plans/learner.md` — §13 Phase 4 + backlog row | **Modify** — retire "NOT YET implemented" framing; point to this file. | +4 / −4 |
| 8 | `scripts/earnings/test_validate_prediction_result.py` | **NEW** (verified absent) — V1–V24. | +130 |
| 9 | `scripts/earnings/test_render_learning_context.py` | **NEW** (verified absent) — R1–R4 renderer tuple tests. | +35 |
| **Total source** | | | **~164** |
| **Total incl. tests** | | | **~329** |

**Deferred (separate PR after ≥10 T1 quarters)**:
- `scripts/earnings/audit_lesson_labels.py` + test (~130 lines)
- `scripts/earnings/result_md_renderer.py` label section (~15 lines)

### 7.1 Regression surface

Consumers of `prediction_result.v1`:
- `earnings_orchestrator.py` (validator + finalizer — this plan)
- `scripts/run_ab_baseline.py`, `run_nvda_ab_sequential.py`, `run_burl_ab_sequential.py`, `run_calibration_sequential.py`, `run_q3_from_existing_bundle.py` — existing readers use `.get()` per inspection; additive fields transparent; this plan wires the kwarg at their validate sites.
- `result_md_renderer.py` — unaware of new fields is safe; sidecar just lacks labels section until the deferred PR adds it.
- `thinking_harvester.py` — reads via try/except; additive fields transparent.

Zero other readers. Grep after commit: `grep -rn "prediction_result\|lesson_labels\|cites_lesson_indices" scripts/ .claude/` to verify no hidden consumer.

Consumers of `_render_learning_context`:
- `render_bundle_text` line 1502 — only caller today. Tuple unpacking is 1-line change.

### 7.2 Consumers of `render_bundle_text`
- `run_core_flow` at `earnings_orchestrator.py:1517` — uses only the text. Unaffected by internal tuple change.

### 7.3 Concrete call sites of `validate_prediction_result` (enumerated — all 6 wired)

All 6 sites empirically verified via `grep -rn "validate_prediction_result(" scripts/earnings/ scripts/run_*.py`. **T1 wires all 6 uniformly** — no active/paused split. The A/B scripts are wired while paused so that A/B reactivation requires zero additional code work. A/B test *runs* remain paused per user directive; the wiring is dormant and benign when those scripts aren't executed.

| Site | File:Line | Bundle source | Wiring (T1) |
|---|---|---|---|
| A | `scripts/earnings/earnings_orchestrator.py:3295` | `bundle` dict in scope from `run_core_flow` | 2 lines: renderer call + kwarg |
| B | `scripts/run_ab_baseline.py:134` | `stripped_bundle: Path` at line 93 → load JSON | 3 lines: `json.loads(stripped_bundle.read_text())` + renderer + kwarg |
| C | `scripts/run_burl_ab_sequential.py:117` | `stripped_bundle: Path` declared at line 95 → load JSON | 3 lines: same pattern as B |
| D | `scripts/run_calibration_sequential.py:76` | `paths["bundle_path"]: Path` via `get_prediction_paths` → load JSON | 3 lines: `json.loads(paths["bundle_path"].read_text())` + renderer + kwarg |
| E | `scripts/run_nvda_ab_sequential.py:112` | `stripped_bundle: Path` declared at line 91 → load JSON | 3 lines: same pattern as B |
| F | `scripts/run_q3_from_existing_bundle.py:84` | `paths["bundle_path"]: Path` at line 58 → load JSON | 3 lines: same pattern as D |

**Universal wiring pattern** (site-specific variable names):
```python
from earnings_orchestrator import _render_learning_context  # add to imports if not already
# Site A: bundle is already in scope (skip the next line)
bundle = json.loads(<bundle_path_var>.read_text(encoding="utf-8"))
_, expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
validate_prediction_result(payload, ticker, quarter_label,
                           expected_lesson_texts=expected_lessons)
```

Where `<bundle_path_var>` is:
- B/C/E: `stripped_bundle`
- D: `paths["bundle_path"]`
- F: `paths["bundle_path"]`

**A/B WITHOUT-lessons semantics**: sites B/C/E run against bundles with `learning_context.ticker_lessons = []` and `global_lessons = []` (stripped). Therefore `expected_lessons = []` at those sites, and the positional check trivially passes. Shape/enum/citation-confirmed/analysis-floor all still fire on any predictor output. Structural coverage is universal.

---

## 8. Implementation details (exact snippets — bot-ready)

### 8.1 `earnings-prediction/SKILL.md` — exact block to insert

**Insert BEFORE current `## Reasoning` at line 30:**

````markdown
## Phase 0 — Label Prior Lessons (MANDATORY before any reasoning)

**Source of truth**: read `bundle.learning_context` from the JSON at `BUNDLE_PATH`. This is a dict with two keys:
- `ticker_lessons: list[dict]` — each with `predictor_lessons: list[str]`, `data_lessons`, `why`, `quarter_label`, etc.
- `global_lessons: list[dict]` — each with `scope` (one of `sector`/`macro`/`cross_ticker`), `lesson: str`, etc.

**What to label**:
- Every string in `ticker_lessons[i].predictor_lessons[j]` (walk `i` in array order, then `j` in array order)
- Every `global_lessons[i].lesson` where `global_lessons[i].scope == "sector"` (in array order)
- Every `global_lessons[i].lesson` where `scope == "macro"` (in array order)
- Every `global_lessons[i].lesson` where `scope == "cross_ticker"` (in array order)

**What NOT to label** (these exist in the bundle/render but are NOT in your label list):
- `ticker_lessons[i].data_lessons[]` — fetch/weight heuristics
- `ticker_lessons[i].why` — metadata
- Quarter header metadata (direction_correct, actual_daily_pct, primary_driver_category)

**Emission order MUST match the traversal above** — the validator compares positionally against an orchestrator-computed expected list. Misordering fails validation.

**For each labeled lesson, answer one question**:

> Does the CURRENT bundle independently show evidence that this lesson's specific mechanism applies?

Emit a label entry with exactly three fields:

- `lesson_text` — the verbatim lesson string, copied from `predictor_lessons[j]` or `global_lessons[i].lesson` with NO paraphrasing
- `label` — strictly one of `"confirmed"` / `"contradicted"` / `"irrelevant"` (lowercase only)
  - `confirmed`: the current bundle independently shows the lesson's mechanism is present
  - `contradicted`: the current bundle shows evidence of the *opposite*
  - `irrelevant`: the lesson's mechanism is absent from the current bundle
- `bundle_evidence` — a 1-sentence citation from the current bundle justifying the label
  - For `irrelevant`: you MAY use the literal string `"no relevant evidence"` or a specific explanation
  - For `confirmed` and `contradicted`: MUST be specific evidence (section/field name + value or quote). The string `"no relevant evidence"` is rejected by the validator for these labels.

**Citation rule (structural)**: every `key_drivers[i]` MUST include `cites_lesson_indices: list[int]` (may be empty `[]`). Each integer references a position in your `lesson_labels[]` array. You may cite a lesson ONLY if its `label == "confirmed"`. The validator rejects citation of `contradicted` or `irrelevant` labels.

**Empty case**: if `bundle.learning_context.ticker_lessons` and `bundle.learning_context.global_lessons` are both empty, emit `"lesson_labels": []` and ensure every `cites_lesson_indices` is `[]`. Do not omit.

**`analysis` field constraint**: your `analysis` free-text must not contain the verbatim normalized `lesson_text` of any lesson whose label is `contradicted` or `irrelevant`. You may paraphrase or omit — not quote. The validator performs a substring check.

**Example** (shape only — do NOT copy phrasings; label based on YOUR current bundle):

```json
"lesson_labels": [
  {
    "lesson_text": "<first labeled lesson, verbatim from learning_context>",
    "label": "irrelevant",
    "bundle_evidence": "no relevant evidence"
  },
  {
    "lesson_text": "<second labeled lesson, verbatim>",
    "label": "confirmed",
    "bundle_evidence": "<1-sentence citation from THIS quarter's bundle>"
  }
],
"key_drivers": [
  { "driver": "<bundle-derived driver>", "direction": "short", "evidence": "<bundle citation>", "cites_lesson_indices": [] },
  { "driver": "<driver supported by lesson>", "direction": "short", "evidence": "<bundle citation>", "cites_lesson_indices": [1] }
]
```
````

**Modify the `## Output` JSON example** (lines 42–59 of current SKILL.md):

Add `"lesson_labels": [...]` before `"key_drivers"`. Add `"cites_lesson_indices": []` inside every example `key_drivers` entry.

**Add two entries to `### Field definitions`** (after existing `evidence_ledger`, before `analysis`):

```markdown
**`lesson_labels`** — required, array (may be `[]` only when `bundle.learning_context.ticker_lessons` and `global_lessons` are both empty). One entry per labeled lesson per §Phase 0. Schema: `{lesson_text, label, bundle_evidence}`.

**`cites_lesson_indices`** (on every `key_drivers[i]`) — required, `list[int]` (may be `[]`). Each integer is a position in `lesson_labels[]`; cited position MUST have `label == "confirmed"`.
```

### 8.2 `_render_learning_context` — tuple refactor

**Current** (line 2485):
```python
def _render_learning_context(learning_ctx: dict) -> str:
    """Render learning context into a readable section for the prediction bundle."""
    parts: list[str] = []
    parts.append("## Prior Lessons (from learner)")

    ticker_lessons = learning_ctx.get("ticker_lessons", [])
    global_lessons = learning_ctx.get("global_lessons", [])

    if not ticker_lessons and not global_lessons:
        parts.append("\nNo prior lessons available (first prediction for this ticker).")
        return "\n".join(parts)

    # … existing body …

    return "\n".join(parts)
```

**New**:
```python
def _render_learning_context(learning_ctx: dict) -> tuple[str, list[str]]:
    """Render learning context and emit the ordered list of LABELED lesson texts.

    Returns (rendered_text, ordered_lesson_texts). The list is the authoritative
    source of truth for T1 lesson_labels positional validation — by construction,
    it is emitted in the same traversal order the render emits. Excludes
    data_lessons and metadata (why, quarter headers) per T1 scope rules.
    """
    parts: list[str] = []
    ordered: list[str] = []  # T1: labeled lesson texts in render order

    parts.append("## Prior Lessons (from learner)")

    ticker_lessons = learning_ctx.get("ticker_lessons", [])
    global_lessons = learning_ctx.get("global_lessons", [])

    if not ticker_lessons and not global_lessons:
        parts.append("\nNo prior lessons available (first prediction for this ticker).")
        return "\n".join(parts), ordered

    if ticker_lessons:
        parts.append(f"\n### Ticker Lessons ({len(ticker_lessons)} most recent quarters)\n")
        for lesson in ticker_lessons:
            ql = lesson.get("quarter_label", "?")
            correct = lesson.get("direction_correct")
            actual = lesson.get("actual_daily_pct")
            pred_dir = lesson.get("predicted_direction", "?")
            cat = lesson.get("primary_driver_category", "?")
            icon = "correct" if correct else "wrong"
            parts.append(f"**{ql}** — prediction {icon} ({pred_dir}), actual {actual:+.2f}%, driver: {cat}")
            for pl in lesson.get("predictor_lessons", []):
                parts.append(f"  - Predictor: {pl}")
                if isinstance(pl, str) and pl.strip():
                    ordered.append(pl)                     # T1: LABELED
            for dl in lesson.get("data_lessons", []):
                parts.append(f"  - Data: {dl}")            # T1: NOT labeled
            why = lesson.get("why")
            if why:
                parts.append(f"  - Why: {why}")            # T1: NOT labeled
            parts.append("")

    if global_lessons:
        by_scope: dict[str, list[dict]] = {"sector": [], "macro": [], "cross_ticker": []}
        for entry in global_lessons:
            by_scope.setdefault(entry.get("scope"), []).append(entry)

        if by_scope["sector"]:
            parts.append(f"\n### Sector Lessons ({len(by_scope['sector'])} entries)\n")
            for entry in by_scope["sector"]:
                ts = entry.get("target_sector") or "?"
                src = entry.get("source_ticker") or "?"
                lesson_text = entry.get("lesson", "")
                parts.append(f"- [sector:{ts}] ({src}) {lesson_text}")
                if isinstance(lesson_text, str) and lesson_text.strip():
                    ordered.append(lesson_text)            # T1: LABELED

        if by_scope["macro"]:
            parts.append(f"\n### Macro Lessons ({len(by_scope['macro'])} entries)\n")
            for entry in by_scope["macro"]:
                src = entry.get("source_ticker") or "?"
                lesson_text = entry.get("lesson", "")
                parts.append(f"- [macro] ({src}) {lesson_text}")
                if isinstance(lesson_text, str) and lesson_text.strip():
                    ordered.append(lesson_text)            # T1: LABELED

        if by_scope["cross_ticker"]:
            parts.append(f"\n### Cross-Ticker Lessons ({len(by_scope['cross_ticker'])} entries)\n")
            for entry in by_scope["cross_ticker"]:
                rt = entry.get("related_tickers") or []
                src = entry.get("source_ticker") or "?"
                lesson_text = entry.get("lesson", "")
                parts.append(f"- [cross:{','.join(rt)}] ({src}) {lesson_text}")
                if isinstance(lesson_text, str) and lesson_text.strip():
                    ordered.append(lesson_text)            # T1: LABELED
        parts.append("")

    return "\n".join(parts), ordered
```

**Update caller** at line 1502:
```python
# BEFORE:
sections.append(_render_learning_context(learning_ctx))
# AFTER:
_text, _ = _render_learning_context(learning_ctx)
sections.append(_text)
```

### 8.3 `_normalize_lesson_text` helper

Insert at module level near the top of the validator section (e.g., just above `validate_prediction_result`):

```python
def _normalize_lesson_text(s: str) -> str:
    """Whitespace-collapse + strip + case-fold for stable comparison.

    Used for both (a) positional equality and (b) analysis substring floor.
    Case-folding absorbs harmless capitalization drift; LLMs do not reliably
    preserve case, and an intentional verbatim quote survives case folding.
    """
    return " ".join((s or "").strip().split()).lower()
```

### 8.4 `validate_prediction_result` — exact additions

**Current state** (line 1574): see §4.2 of rev 2 for the existing body.

**Signature change**: add `, *, expected_lesson_texts: list[str] | None = None`.

**Add `"lesson_labels"`** to the `required` list at line 1578–1594. Insert it right after `"analysis"` (which is the last LLM-written field) and before `"predicted_at"` (the first Python-owned metadata field). This keeps the list's logical grouping intact: identity → LLM-analytic → Python metadata.

**INSERT new validation blocks** after the existing `analysis` non-empty check (line 1639):

```python
# ══════════════════════════════════════════════════════════════════
# T1 — lesson_labels validation (template-overfit mitigation)
# ══════════════════════════════════════════════════════════════════
_LABEL_ENUM = {"confirmed", "contradicted", "irrelevant"}

labels = payload.get("lesson_labels")
if labels is None:
    raise ValueError("lesson_labels must be a list, got null")
if not isinstance(labels, list):
    raise ValueError(f"lesson_labels must be a list, got {type(labels).__name__}")

# ─ Shape + enum + non-empty + sentinel discipline ─
for i, entry in enumerate(labels):
    if not isinstance(entry, dict):
        raise ValueError(f"lesson_labels[{i}] must be an object")
    for req in ("lesson_text", "label", "bundle_evidence"):
        if req not in entry:
            raise ValueError(f"lesson_labels[{i}] missing required field: {req}")
    lbl = entry["label"]
    if lbl not in _LABEL_ENUM:
        raise ValueError(
            f"lesson_labels[{i}].label must be one of {sorted(_LABEL_ENUM)}, got {lbl!r}"
        )
    for sf in ("lesson_text", "bundle_evidence"):
        if not isinstance(entry[sf], str):
            raise ValueError(f"lesson_labels[{i}].{sf} must be a string")
    if not entry["lesson_text"].strip():
        raise ValueError(f"lesson_labels[{i}].lesson_text must be non-empty")
    evidence = entry["bundle_evidence"].strip()
    if not evidence:
        raise ValueError(f"lesson_labels[{i}].bundle_evidence must be non-empty")
    # Sentinel discipline: 'no relevant evidence' is reserved for irrelevant
    if lbl in ("confirmed", "contradicted") and evidence.lower() == "no relevant evidence":
        raise ValueError(
            f"lesson_labels[{i}]: {lbl!r} requires specific bundle_evidence; "
            f"'no relevant evidence' sentinel is reserved for 'irrelevant'"
        )

# ─ Positional equality against orchestrator-computed expected list ─
if expected_lesson_texts is not None:
    if len(labels) != len(expected_lesson_texts):
        raise ValueError(
            f"lesson_labels has {len(labels)} entries; "
            f"expected {len(expected_lesson_texts)} (from bundle.learning_context render order)"
        )
    for i, (got, want) in enumerate(zip(labels, expected_lesson_texts)):
        if _normalize_lesson_text(got["lesson_text"]) != _normalize_lesson_text(want):
            raise ValueError(
                f"lesson_labels[{i}].lesson_text does not match expected "
                f"(normalized comparison failed at position {i})"
            )

# ─ cites_lesson_indices: confirmed-only ─
for i, kd in enumerate(payload["key_drivers"]):
    if "cites_lesson_indices" not in kd:
        raise ValueError(f"key_drivers[{i}].cites_lesson_indices is required (may be empty list)")
    cites = kd["cites_lesson_indices"]
    if not isinstance(cites, list):
        raise ValueError(f"key_drivers[{i}].cites_lesson_indices must be a list")
    for j, idx in enumerate(cites):
        # Reject bool-as-int (Python quirk: isinstance(True, int) is True)
        if not isinstance(idx, int) or isinstance(idx, bool):
            raise ValueError(
                f"key_drivers[{i}].cites_lesson_indices[{j}] must be int, got {type(idx).__name__}"
            )
        if not (0 <= idx < len(labels)):
            raise ValueError(
                f"key_drivers[{i}].cites_lesson_indices[{j}] = {idx} out of range "
                f"(len(lesson_labels)={len(labels)})"
            )
        if labels[idx]["label"] != "confirmed":
            raise ValueError(
                f"key_drivers[{i}].cites_lesson_indices[{j}] = {idx} cites lesson with "
                f"label={labels[idx]['label']!r}; only 'confirmed' labels may be cited"
            )

# ─ Analysis-field substring floor: reject verbatim quote of non-confirmed lesson ─
# Length guard at 30 chars: below this, substring match risks innocent
# collision on common short phrases (e.g. "margin pressure continued").
# Real learner lessons are 80–150 chars — guard is cheap insurance.
# Case-fold is applied by _normalize_lesson_text for both sides.
_ANALYSIS_MIN_LEN = 30
analysis_norm = _normalize_lesson_text(payload["analysis"])
for i, entry in enumerate(labels):
    if entry["label"] == "confirmed":
        continue
    lt_norm = _normalize_lesson_text(entry["lesson_text"])
    if len(lt_norm) < _ANALYSIS_MIN_LEN:
        continue  # too short for reliable substring match; paraphrase-evasion already acknowledged (§2.2)
    if lt_norm in analysis_norm:
        raise ValueError(
            f"analysis contains verbatim lesson_labels[{i}].lesson_text "
            f"(label={entry['label']!r}); paraphrase or omit — may not quote"
        )
```

### 8.5 Caller wiring at 6 sites

For each site in §7.3, add **2 or 3 lines** just before the `validate_prediction_result(...)` call:
- **Site A** (`earnings_orchestrator.py`): **2 lines** — bundle dict is already in scope; just call renderer + pass kwarg.
- **Sites B, C, D, E, F** (runner scripts): **3 lines** — bundle is a `Path` (not a dict); add one `json.loads(...read_text())` before the renderer call + pass kwarg.

**Pattern** (adjust `bundle`/`<bundle_path_var>` per site — Site A omits the first line since `bundle` is already in scope):
```python
bundle = json.loads(<bundle_path_var>.read_text(encoding="utf-8"))  # Sites B/C/D/E/F only
_, _expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
validate_prediction_result(
    payload, ticker, quarter_label,
    expected_lesson_texts=_expected_lessons,
)
```

**Import note** (all 6 sites): `_render_learning_context` must be importable at each caller.
- Site A (same module): no import needed.
- Sites B/C/D/E/F: add `from earnings_orchestrator import _render_learning_context` at the top if not already imported.

**Per-site wiring** (all 6 sites — uniform coverage):

- **Site A** (`earnings_orchestrator.py:3295`): `bundle` dict in scope. Import already in-module:
  ```python
  _, _expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
  validate_prediction_result(prediction, expected_ticker=args.ticker,
                             expected_quarter=quarter_info["quarter_label"],
                             expected_lesson_texts=_expected_lessons)
  ```

- **Site B** (`run_ab_baseline.py:134`): `stripped_bundle` is a `Path` at line 93. Wire before the existing validate call:
  ```python
  bundle = json.loads(stripped_bundle.read_text(encoding="utf-8"))
  _, _expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
  validate_prediction_result(no_lessons, "AVGO", ql,
                             expected_lesson_texts=_expected_lessons)
  ```
  Add `from earnings_orchestrator import _render_learning_context` to existing imports. `_expected_lessons` will be `[]` because the A/B path strips `learning_context`.

- **Site C** (`run_burl_ab_sequential.py:117`): `stripped_bundle: Path` at ~line 105. Same pattern as B with `TICKER="BURL"`:
  ```python
  bundle = json.loads(stripped_bundle.read_text(encoding="utf-8"))
  _, _expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
  validate_prediction_result(json.loads(test_result_path.read_text()), TICKER, label,
                             expected_lesson_texts=_expected_lessons)
  ```

- **Site D** (`run_calibration_sequential.py:76`): inside `finalize_and_learn`, bundle NOT in scope. `paths["bundle_path"]` provides it. After `prediction = json.loads(paths["result_path"].read_text())` at line 75:
  ```python
  bundle = json.loads(paths["bundle_path"].read_text(encoding="utf-8"))
  _, _expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
  validate_prediction_result(prediction, TICKER, quarter_label,
                             expected_lesson_texts=_expected_lessons)
  ```
  Add `from earnings_orchestrator import _render_learning_context` to existing imports.

- **Site E** (`run_nvda_ab_sequential.py:112`): `stripped_bundle: Path` at ~line 100. Same pattern as B with `TICKER="NVDA"`:
  ```python
  bundle = json.loads(stripped_bundle.read_text(encoding="utf-8"))
  _, _expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
  validate_prediction_result(json.loads(test_result_path.read_text()), TICKER, label,
                             expected_lesson_texts=_expected_lessons)
  ```

- **Site F** (`run_q3_from_existing_bundle.py:84`): `paths["bundle_path"]` in scope at line 58:
  ```python
  bundle = json.loads(paths["bundle_path"].read_text(encoding="utf-8"))
  _, _expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
  validate_prediction_result(prediction, TICKER, quarter_info["quarter_label"],
                             expected_lesson_texts=_expected_lessons)
  ```
  Add import if missing.

**All 6 sites pass `expected_lesson_texts` → positional enforcement is universal across the repo's entire validate surface.** A/B sites (B/C/E) have `expected = []` because the A/B path strips the learning_context — positional check trivially satisfied; shape/enum/citation/analysis-floor still fire.

### 8.6 Plan-doc sync — `learner.md`

At the "🔴 Next up" backlog table, update the T1 row to:
```
| T1 | … | ✅ **shipped in commit <hash>** — see ``.claude/plans/learner.md` Appendix B` (rev 3) |
```

At §13 Phase 4's "Proposed mitigation for template overfit" heading, add one line near the top:
```
> **STATUS**: shipped <date> as ``.claude/plans/learner.md` Appendix B` (rev 3). Spec below retained as historical design context only.
```

---

## 9. Test matrix

### 9.1 Validator tests — `test_validate_prediction_result.py`

| # | Test | Expected |
|---|---|---|
| V1 | All required fields valid; `lesson_labels=[]`, `expected=[]`, every driver `cites_lesson_indices=[]` | passes |
| V2 | 3 labels in order; `expected` matches positionally; drivers cite only `confirmed` indices | passes |
| V3 | `lesson_labels` field absent | raises `lesson_labels` missing |
| V4 | `lesson_labels: null` | raises |
| V5 | `lesson_labels` is a string | raises type |
| V6 | Entry missing `label` | raises `label` missing |
| V7 | `label="maybe"` | raises enum |
| V8 | `label="CONFIRMED"` (wrong case) | raises enum |
| V9 | `lesson_text=""` | raises non-empty |
| V10 | `bundle_evidence=""` | raises non-empty |
| V11 | `expected` has 3, `lesson_labels` has 2 | raises length mismatch |
| V12 | `expected` has 3, `lesson_labels` has 4 (fabrication) | raises length mismatch |
| V13 | Length matches but `lesson_labels[1].lesson_text` differs post-normalization | raises positional mismatch |
| V14 | Trailing/interior whitespace diff between text and expected (post-normalize equal) | passes |
| V15 | `key_drivers[i]` missing `cites_lesson_indices` | raises |
| V16 | `cites_lesson_indices=[0]` where `lesson_labels[0].label="irrelevant"` | raises "only 'confirmed' may be cited" |
| V17 | `cites_lesson_indices=[0]` where `lesson_labels[0].label="contradicted"` | raises |
| V18 | `cites_lesson_indices=[5]` but `len(labels)=3` | raises out of range |
| V19 | `cites_lesson_indices=[True]` (bool) | raises type |
| V20 | `expected_lesson_texts=None` (audit mode); shape valid; skip positional | passes |
| V21 | `label="confirmed"` + `bundle_evidence="no relevant evidence"` | raises sentinel violation |
| V22 | `analysis` contains verbatim normalized lesson_text of an `irrelevant` label | raises analysis leak |
| V23 | `analysis` contains verbatim normalized lesson_text of a `confirmed` label | passes (citation allowed) |
| V24 | `analysis` paraphrases an `irrelevant` lesson but never quotes it verbatim | passes (substring floor acknowledges paraphrase-evasion) |

### 9.2 Renderer tests — `test_render_learning_context.py`

| # | Test | Expected |
|---|---|---|
| R1 | Empty `learning_context` | returns `(text_with_first_prediction_message, [])` |
| R2 | Ticker lessons with `predictor_lessons + data_lessons + why` — list excludes data + why | list length = sum of predictor_lessons only |
| R3 | Globals: 2 sector + 1 macro + 2 cross_ticker — list order is sector, sector, macro, cross, cross | exact list match |
| R4 | Mixed ticker + global — render text contains all bullets; list contains only labeled lessons in order | pass |

### 9.3 Integration tests

| # | Test | Expected |
|---|---|---|
| I1 | Full predict flow with mocked SDK producing valid labels matching renderer's list | writes valid `prediction/result.json`; validator passes |
| I2 | SDK emits `lesson_labels=[]` when renderer listed 3 lessons | validator rejects length mismatch |
| I3 | SDK cites `irrelevant` lesson in `cites_lesson_indices` | validator rejects |
| I4 | A/B baseline (WITHOUT-lessons): bundle has blanked learning_context; LLM must emit `lesson_labels=[]` and every `cites_lesson_indices=[]` | validator passes with `expected=[]` |
| I5 | Re-validation of written result.json with `expected=None` (audit mode) | passes shape, skips positional |
| I6 | SDK's `analysis` quotes an `irrelevant` lesson verbatim | validator rejects; retry fires |

---

## 10. Deferred — audit script

Per rev-2 reasoning: zero T1 quarters exist at ship time. Threshold calibration (70%/85%) is a priori guessing until real distribution is observed.

**When to ship**: after ≥10 T1 quarters on the post-wipe corpus.

**Draft spec** (retained for future implementer):
- `scripts/earnings/audit_lesson_labels.py`
- Walks `Companies/*/events/*/prediction/result.json`
- Per-ticker aggregates: `quarters_scored`, label-count distribution, `confirmed_rate`
- Sample guard: `status = "INSUFFICIENT_DATA"` if `quarters_scored < 3` OR `total_labels < 10`
- Thresholds (calibrate against real data): tentative WARN > 70%, FLAG > 85%
- Output: text (default), `--json`, `--ticker <TICKER>`
- Companion test `test_audit_lesson_labels.py`
- If FLAG triggers on ≥3 tickers: escalate to label-only-LLM (design sketch in `learner.md` §13 Phase 4)

---

## 11. Rollout — single atomic commit

### 11.1 Pre-commit checklist

- [ ] **Task #356 corpus wipe complete** (or explicit acceptance of caveat)
- [ ] All new/modified files `py_compile` clean
- [ ] V1–V24 + R1–R4 + I1–I6 green
- [ ] Existing predictor tests still pass (regression check)
- [ ] Grep confirms **all 6** call sites are wired with `expected_lesson_texts=`:
  ```bash
  # NOTE: --exclude-dir=__pycache__ + --exclude=test_*.py (file-level exclude, NOT
  # line-level `-v test_` — line-level filter accidentally drops lines containing
  # the `test_result_path` variable name used in A/B runners).
  grep -rn "validate_prediction_result(" scripts/ \
      --include="*.py" --exclude-dir=__pycache__ --exclude="test_*.py" \
    | grep -v "def validate"
  ```
  must return exactly 6 lines (line numbers may shift ± a few):
  1. `scripts/earnings/earnings_orchestrator.py:<~3295>`
  2. `scripts/run_ab_baseline.py:<~134>`
  3. `scripts/run_burl_ab_sequential.py:<~117>`
  4. `scripts/run_calibration_sequential.py:<~76>`
  5. `scripts/run_nvda_ab_sequential.py:<~112>`
  6. `scripts/run_q3_from_existing_bundle.py:<~84>`

  **Universal-wiring assertion** — every one of these call sites must pass the kwarg as a real argument (not the function-def default):
  ```bash
  # Match the KWARG invocation pattern 'expected_lesson_texts=_expected_lessons'
  # explicitly — this excludes the function-def default (which uses
  # ': list[str] | None = None' with a colon type annotation and NO equals-sign
  # directly after the identifier). Excludes test files via --exclude.
  grep -rn "expected_lesson_texts=_expected_lessons" scripts/ \
      --include="*.py" --exclude-dir=__pycache__ --exclude="test_*.py" \
    | wc -l
  ```
  must return `6` (one invocation per call site, exactly 6).
- [ ] Each runner script (5 sites outside the orchestrator) has the specific new bundle-load line introduced by T1 (not pre-existing `read_text()` calls for other purposes):
  - For A/B runners (B, C, E) — bundle source is `stripped_bundle`:
    ```bash
    grep -c "stripped_bundle\.read_text" scripts/run_ab_baseline.py scripts/run_burl_ab_sequential.py scripts/run_nvda_ab_sequential.py
    ```
    must return `1` for each (exactly the new T1 bundle-load line).
  - For orchestrator-path runners (D, F) — bundle source is `paths["bundle_path"]`:
    ```bash
    grep -c 'paths\["bundle_path"\]\.read_text' scripts/run_calibration_sequential.py scripts/run_q3_from_existing_bundle.py
    ```
    must return `1` for each.
  - Combined: total new bundle-load lines across runner files = 5 (one per site B/C/D/E/F).
- [ ] Grep confirms no `_extract_expected_lesson_texts` helper introduced (rev-3 uses renderer tuple, not a separate extractor)
- [ ] Grep confirms no PreToolUse hook file created for predictor: `ls .claude/hooks/validate_prediction*` returns "no such file"
- [ ] Dry-run one AVGO quarter via CLI: `python3 scripts/earnings/earnings_orchestrator.py AVGO <accession> --save --predict --learn` → inspect `prediction/result.json` for valid `lesson_labels` + `cites_lesson_indices`
- [ ] **A/B smoke SKIPPED** — running A/B is paused per user directive (2026-04-19), but sites B/C/E are nonetheless wired in T1 per §7.3 so positional enforcement is universal. A/B scripts are dormant-but-ready; when A/B reactivates, zero additional code work is needed — just start running them. Re-add a dry-run check for WITHOUT-lessons path when that happens.
- [ ] `jq '.lesson_labels | length' earnings-analysis/Companies/AVGO/events/<Q>/prediction/result.json` matches the expected lesson count for that quarter
- [ ] `jq '[.key_drivers[] | has("cites_lesson_indices")] | all' ...` returns `true` (every driver has the field)

### 11.2 Commit

Title: `feat(predictor): T1 — structurally-enforced labeled lesson consumption`

Body references this plan. Includes:
- Empirical cases (AVGO Q3, BURL Q1)
- Structural over prompt enforcement (cites_lesson_indices + positional + sentinel + analysis-floor)
- No hook; renderer is single source of truth
- Corpus prerequisite (#356)

### 11.3 Post-commit smoke

**Scope note**: A/B testing RUNS are paused (user directive 2026-04-19), but all 6 sites are wired. Smoke exercises Sites A and D; Sites B/C/E/F remain dormant but wiring is static-asserted by §11.1 pre-commit greps.

1. Run one AVGO WITH-lessons quarter via orchestrator CLI on the post-wipe corpus (exercises Site A):
   ```bash
   python3 scripts/earnings/earnings_orchestrator.py AVGO <AVGO_accession_8k> --save --predict --learn
   ```
2. Inspect `prediction/result.json`: label distribution not all-`confirmed`; `cites_lesson_indices` present on every driver and references only `confirmed` labels; `analysis` has no verbatim non-confirmed quotes of lessons ≥30 chars.
3. Deliberately corrupt via manual edit (e.g., set a `label` to `"MAYBE"`) and re-invoke the validator directly from a Python REPL on the modified file — confirm rejection.
4. Re-run the full 3-AVGO quarters via the calibration harness (exercises Site D including its bundle-load):
   ```bash
   python3 scripts/run_calibration_sequential.py
   ```
   Confirm: all 3 quarters validate cleanly; Site D's bundle-load path fires on each.
5. **Sites not exercised by T1 ship smoke** (B/C/E are A/B runners currently paused; F is an on-demand diagnostic): wiring is static-asserted via §11.1 pre-commit greps (`expected_lesson_texts=` present at each call site). Dynamic exercise happens when A/B is reactivated (B/C/E) or when the operator next invokes the Q3 diagnostic (F).

### 11.4 Rollback — honest version

If systemic label-dishonesty emerges (retry-rate > 30% sustained across ≥5 quarters):

**What rollback actually requires** (there is no SKILL-only shortcut — structural enforcement lives in the validator):

1. **SKILL.md** — downgrade Phase 0's "MUST NOT cite contradicted/irrelevant" language to advisory ("should avoid citing"). ~5 lines.
2. **Validator** — concurrently relax the citation-confirmed check from `raise ValueError` to `log.warning` (one 3-line edit at the `cites_lesson_indices` block). Optionally gate behind an env var `T1_STRICT_CITATIONS=false`.

**Both changes must land in the same commit.** Reverting SKILL.md alone leaves the validator enforcing — the validator still rejects, the LLM output is rejected, the quarter still fails. Rollback is a ~20-line coordinated edit, not a 5-line SKILL-only nudge.

**Schema (`lesson_labels`, `cites_lesson_indices`) stays in all rollback scenarios.** Audit-only metadata is strictly better than pre-T1.

**What to preserve in rollback**: shape + enum + non-empty + sentinel + positional equality + analysis substring floor. These are observability and data-integrity — not part of the template-overfit hypothesis being rolled back.

---

## 12. Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **Paraphrased prose-leak in `analysis`** — LLM mentions an irrelevant lesson without verbatim quoting | Medium | Low | Substring floor catches verbatim; paraphrase requires semantic comparison (out of scope). Explicit residual per §2.2. Detectable offline by future audit. |
| R2 | **Confirmation bias in self-labeling** — same LLM decides if its own lesson applies | Medium | Medium | Deferred audit flags >70% confirmed-rate. Escalation to label-only LLM per learner.md §13 Phase 4. |
| R3 | **Order drift** — LLM emits labels in different order than renderer produced | Low | Low | Renderer is single source of truth — LLM reads same JSON, follows same traversal. Positional check catches any drift with descriptive error; retry self-corrects. |
| R4 | **Whitespace/unicode drift** between bundle text and label entry | Low | Low | `_normalize_lesson_text` handles whitespace. Paraphrasing fails → retry. |
| R5 | **Transient retry-rate increase** during first N T1 quarters | Certain (early) | Low | Existing 1-retry path in orchestrator. LearnerOutcome-style observability via run_ledger (task #362 pattern). |
| R6 | **A/B WITHOUT-lessons path regression** — validator requires `lesson_labels` even when bundle is blanked | Low | Medium | LLM must emit `lesson_labels=[]`; expected=[]. I4 test covers explicitly. |
| R7 | **Legacy/audit callers without bundle** | Certain | None | `expected_lesson_texts=None` skips positional check; shape/enum/citation still enforced. |
| R8 | **Thinking harvester compatibility** | Low | Low | Harvester uses `.get()` + try/except. Additive fields transparent. Verify in 11.1 smoke. |
| R9 | **finalize_prediction_result overwrites LLM fields** | Low | High | Verified at line 2944: field-by-field `payload[k]=...` pattern. Additive fields survive. |
| R10 | **Renderer tuple caller miss** | Low | Medium | Only 1 caller today (line 1502). Change is 2 lines. Grep `_render_learning_context(` after commit confirms all callers unpack. |

---

## 13. Pre-verified implementation facts (resolved during rev-3 authoring)

All items below were empirically checked against live code before rev-3 finalization. No open questions remain for the implementer.

| # | Fact | Verified by |
|---|---|---|
| 1 | **Predictor retry path**: The predictor flow at `earnings_orchestrator.py:3284-3299` has no informed-retry (unlike the learner's H2 path at lines ~2019-2053). Validator failure raises and stops the quarter. **Do NOT add informed-retry in this PR** — orthogonal to T1 and potentially scope-creep. | `grep -n "retry" earnings_orchestrator.py` shows retry logic only in builder transient-failure helper and in `run_learner_for_quarter` |
| 2 | **finalize_prediction_result preservation**: line 2944+ uses field-by-field `payload[k] = ...` (no dict-replacement pattern). `lesson_labels` and `cites_lesson_indices` written by the LLM survive finalize. | `grep -n "payload\[" earnings_orchestrator.py` at lines 2954-2979 confirms additive assignment only |
| 3 | **Site D bundle scope**: NO bundle in scope at the validate call (inside `finalize_and_learn`). Resolved via `json.loads(paths["bundle_path"].read_text())` per §8.5 wiring snippet. | Read of `run_calibration_sequential.py:57-79` confirmed |
| 4 | **Test-file existence**: `test_validate_prediction_result.py` and `test_render_learning_context.py` do NOT exist today. Create both as NEW files per §7 inventory. | `ls scripts/earnings/test_validate_prediction_result.py scripts/earnings/test_render_learning_context.py` returns "no such file" |
| 5 | **`_render_learning_context` import** for scripts/run_*.py: existing convention is `from earnings_orchestrator import <symbol>` (via the sys.path insert in each script's header). Add `_render_learning_context` to existing import lines per site. | `head -30 scripts/run_ab_baseline.py` shows import style |
| 6 | **`BUNDLE_PATH` resolves to `context_bundle.json` (JSON, not rendered text)**: orchestrator passes `bundle_path=context_bundle.json` via the `BUNDLE_PATH=` line in the predictor prompt (line 3081). SKILL.md Phase 0's "read `bundle.learning_context` from the JSON" instruction is accurate. | Read of `earnings_orchestrator.py:3079-3085` confirmed |
| 7 | **AVGO-specific sequential A/B**: no dedicated `run_avgo_ab_sequential.py` exists. Use `run_ab_baseline.py` (which is AVGO-specific) or the orchestrator CLI per §11.3. | `ls scripts/run_avgo_*` returns "no such file" |

---

## 14. Dependencies

| Dep | Status |
|---|---|
| T1.5a + T1.5b PIT correctness | ✅ shipped |
| T3 sector-at-source | ✅ shipped |
| Corpus wipe + 15-quarter rerun (#356) | ⏳ pending |
| Existing `validate_prediction_result` at line 1574 | ✅ |
| Existing `_render_learning_context` at line 2485 | ✅ — gets refactored |
| LearnerOutcome / run_ledger (#362) | ✅ — reuse for retry observability |

---

## 15. Rejected alternatives (pruned from rev-2; only decision-relevant kept)

| Alternative | Why rejected |
|---|---|
| Add PreToolUse Write hook for predictor | Zero unique reliability vs Python validator; no derived-write recovery path (learner's reason doesn't apply); adds ~65 lines incl tests + settings registration + drift surface. |
| Separate `_extract_expected_lesson_texts` helper (rev-2) | Two functions that must stay in sync with each other is a forever-invariant. Renderer-returns-tuple eliminates the invariant by construction. |
| Dedicated `lesson_id` field (hash/UUID) | Positional indices with verbatim `lesson_text` are already unambiguous. IDs add schema + hash-stability rules for zero gain. |
| Label `data_lessons[]` as well | Non-directional (fetch/weight); would inflate confirmed-rate + add token cost without overfit-reduction benefit. |
| Top-level `applied_lesson_ids[]` | Per-driver `cites_lesson_indices` is strictly more structural — binds citation to a specific driver. |
| Additional SKILL.md prose "don't over-apply" | Rev-1's approach; empirically failed (AVGO Q3, BURL Q1). Soft rules don't stably change LLM behavior. |
| Semantic analysis-field check via second LLM | Reintroduces confirmation bias + 2x cost. Substring floor is the cheap-structural-signal; paraphrase evasion accepted per R1. |
| Ship audit script with T1 | Premature — thresholds are a priori guesses until real T1 distribution. |
| Backward-compat default (missing `lesson_labels` → `[]`) at runtime | Corpus is being wiped; would let a forgetful LLM pass silently. |

---

## 16. References

- `scripts/earnings/earnings_orchestrator.py:1574-1639` — current `validate_prediction_result`
- `scripts/earnings/earnings_orchestrator.py:2485-2547` — current `_render_learning_context`
- `scripts/earnings/earnings_orchestrator.py:2921-3003` — `finalize_prediction_result` (additive-field-safe)
- `scripts/earnings/earnings_orchestrator.py:3295` — main predict-flow validate call
- `.claude/skills/earnings-prediction/SKILL.md` — current predictor contract
- `.claude/hooks/validate_learning_output.py` — hook pattern (NOT mirrored; kept for learner only)
- `.claude/settings.json:29-48` — PreToolUse hook registration (not extended by this plan)
- `.claude/plans/learner.md` §13 Phase 4 — original design sketch (historical)
- Task #362 (LearnerOutcome) — retry-observability pattern

---

## 17. Final sign-off checklist

- [ ] Two structural fixes understood — positional equality (via renderer tuple return) + `cites_lesson_indices` (confirmed-only) — these are what make T1 structural, not prompt-governed
- [ ] `data_lessons[]` exclusion accepted as deliberate scoping (directional template overfit is the bug)
- [ ] Audit script deferred to post-T1 data collection
- [ ] Corpus wipe (#356) prerequisite accepted
- [ ] No PreToolUse hook — accepted as correct minimalism (asymmetry with learner is deliberate)
- [ ] Renderer-returns-tuple pattern accepted — single source of truth for lesson order
- [ ] `bundle_evidence` sentinel check restored (rev-1 regression fixed)
- [ ] Analysis-field substring floor added; residual paraphrase-evasion accepted explicitly (§2.2, R1)
- [ ] All 6 validate call sites pre-enumerated (§7.3)
- [ ] Rollback = ~20-line coordinated SKILL.md + validator edit (per §11.4 honest rewrite); schema never reverts; no SKILL-only shortcut exists (validator enforcement lives in Python, not prompt)

---

**End of plan (rev 3).**

**Author**: Claude session 2026-04-19, rev 3. Empirically verified every claim in ChatGPT's and Claude's critiques against live code at `.claude/hooks/validate_learning_output.py`, `.claude/settings.json:29-48`, `scripts/earnings/earnings_orchestrator.py:1574,2485,3295`, all 6 `validate_prediction_result` call sites, A/B scripts at `scripts/run_ab_baseline.py:134`, `run_burl_ab_sequential.py:117`, `run_calibration_sequential.py:76`, `run_nvda_ab_sequential.py:112`, `run_q3_from_existing_bundle.py:84`. Every design decision traced to either a structural invariant or an explicitly-acknowledged residual risk.
