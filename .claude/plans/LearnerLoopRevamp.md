# Learner Loop Revamp — Production Plan (v2 — corrections applied)

**Status**: design locked after second-round review. Ready for implementation sign-off.
**Authors**: Claude + ChatGPT cross-review (3 rounds).
**Last updated**: 2026-05-04.
**Predecessors**: v1 of this file (now in §18 appendix); §13 of `.claude/plans/prediction_learnerSkillsRedo.md` (prose-only MVP — superseded).

This is the round-6 final plan: **v3-only learner schema, fresh-start cutover, no legacy paths, rubric-only prompt (no concrete examples to anchor LLM).** The architecture went through 6 rounds of cross-review (Claude + ChatGPT). All blocking issues found in successive rounds are merged. Substantive evolution:

- **D17**: status is COMPUTED (not stored). Single source of truth = `audit_history`.
- **D18**: aggregator runs in BOTH success and recovery paths.
- **D19**: orchestrator-level cross-file validation (audit ↔ prediction) is required.
- **B1 fix**: PIT filter applies to `audit_history` entries at render time (not just lesson-level).
- **B2 fix**: ~~legacy lessons with `mechanism: null` start in `watch`~~ — obsolete (round 6 fresh-start: no legacy lessons exist post-cutover).
- **B3 fix**: validator cross-checks `evidence_refs` against the same payload's `evidence_ledger`.
- **N3 included**: new lessons (predictor_lessons + global_observations) require `evidence_refs`.
- **N1 included**: drop the 20-entry audit cap (storage cost trivial; cap broke replay observability).
- **Renderer**: `ordered_lesson_texts` = lesson BODY ONLY (not mechanism/status decoration); validator T1 unchanged.

---

## 1. Executive summary

Today's pipeline records every signal needed for a closed loop — predictor labels, citations, actual returns, learner explanations — but consumes none of them to update lesson health. Bad lessons survive forever; good lessons get equal weight to brand-new ones; pattern-matching dressed as causal rules is the dominant failure mode.

The fix is small and surgical:

1. **Bump learner schema to `attribution_result.v3`** (v3-only; no v2 read-compat — round 6 fresh-start cutover).
2. **Lessons become structured dicts** carrying `lesson + mechanism + applies_when + invalid_if + evidence_refs`. Storage stays quarter-row-shaped on the ticker side; global storage already lesson-rowed.
3. **Learner emits `lesson_audit[]`** — exactly one entry per `prediction.lesson_labels[i]`. Each entry carries `review` (helped / misled / outweighed / missed / neutral / unclear), `action` (keep / refine / retire), and `evidence_refs` grounded in the learner's evidence_ledger.
4. **Python aggregator** is the only state-mutating component: applies audits to the right library entries by `lesson_id`, registers refinements with `parent_id`. It RUNS IN BOTH success and recovery paths. Status is NOT stored — it's computed at read time.
5. **`build_learning_context` PIT-filters audit_history per lesson**, then computes a render-time status per lesson via the deterministic state machine. Retired lessons are filtered out; watch lessons render with caution.
6. **Same-quarter self-leak guard** added to `build_learning_context` (lesson-level, both ticker and global).
7. **Orchestrator-level cross-file validation** asserts that `lesson_audit[]` count, indices, lesson_text, predictor_label, and was_cited all match the prediction file.

**Net code delta**: ~500 lines added / ~50 removed across 6 existing source files, plus ~13 new test files (round 6 fresh-start: no migration script needed; v2 read-compat removed; legacy lifecycle test removed). **No new runtime services, agents, schedules, or DBs.** The same code path runs in live and historical (only PIT plumbing differs; already correct).

**Live trading orientation** (clarification): the deployment use case is live trading, not just historical backtesting. PIT plumbing serves backtest correctness (B1 audit-history filter, lesson-level `_passes_pit`); the live-trading correctness story is a different but overlapping set: (1) **no self-leak** (D13 same-quarter guard fires regardless of mode), (2) **fast feedback** (post-event aggregator updates audit_history immediately so the next live prediction sees improved state), (3) **bad lessons stop hurting future calls** (status state machine: misled → watch → retired), (4) **lessons stay causal** (mechanism + applies_when + invalid_if + evidence_refs structural guard, plus prompt-level discipline in §9.1), (5) **predictor doesn't over-trust prior wins** (mechanism gate requires THIS bundle to independently establish causal chain before `confirmed`). The plan is **live-ready by construction** but **live-proven only after the §13.5 G2 (PIT leak) + G3 (full-loop) + G10 (real SDK smoke) gates pass against real data.**

---

## 2. The closed-loop architecture

```
                     ┌──────────────────────────────────────────────┐
                     │           Bundle for Q_n                     │
                     │   ## Lessons To Label                        │
                     │     L1. [scope] [status: ...] [reviews: ...] │
                     │       Lesson: <body>            ← lesson_text│
                     │       Mechanism: ...                         │
                     │       Applies when: ...                      │
                     │       Invalid if: ...                        │
                     │     ...                                      │
                     │   (status + reviews are PIT-filtered views)  │
                     └────────────────┬─────────────────────────────┘
                                      ▼
                     ┌──────────────────────────────────────────────┐
                     │           Predictor Q_n                      │
                     │  • mechanism gate: confirm only if THIS      │
                     │    bundle independently establishes it       │
                     │  • copy ONLY the "Lesson:" body into         │
                     │    lesson_text (validator T1)                │
                     │  • cite confirmed lessons in key_drivers     │
                     │  • write lesson_labels[i] + cites_lesson_idx │
                     └────────────────┬─────────────────────────────┘
                                      │
                                      │ stock moves; actual_return measured
                                      ▼
                     ┌──────────────────────────────────────────────┐
                     │           Learner Q_n                        │
                     │  Phase 1.5  read prediction.lesson_labels    │
                     │             + cites_lesson_indices           │
                     │  Phase 4    write lesson_audit[] — full      │
                     │             coverage; review + action +      │
                     │             evidence_refs                    │
                     │  Phase 4    write NEW lessons (mechanism +   │
                     │             applies_when + invalid_if +      │
                     │             evidence_refs)                   │
                     └────────────────┬─────────────────────────────┘
                                      ▼
                     ┌──────────────────────────────────────────────┐
                     │      Orchestrator post-learner               │
                     │  • validate_attribution_result (v3 schema)   │
                     │  • cross-file check vs prediction (D19):     │
                     │      - len(lesson_audit) == len(lesson_labels)
                     │      - each audit's lesson_text matches      │
                     │        bundle's body at lesson_index         │
                     │      - predictor_label matches               │
                     │      - was_cited matches cites_lesson_indices│
                     │  • append_ticker_lesson + append_global      │
                     │  • aggregate_lesson_audits  (NEW)            │
                     │                                              │
                     │  RECOVERY PATH ALSO calls aggregator (D18)   │
                     └────────────────┬─────────────────────────────┘
                                      ▼
                     ┌──────────────────────────────────────────────┐
                     │      Library state (audit_history is the     │
                     │      canonical fact log; status is a         │
                     │      derived view, not stored)               │
                     └────────────────┬─────────────────────────────┘
                                      │  next quarter
                                      ▼
                     ┌──────────────────────────────────────────────┐
                     │      build_learning_context (next Q)         │
                     │  • lesson PIT filter: source_pit_cutoff      │
                     │  • same-(ticker, quarter) self-leak guard    │
                     │  • PER-LESSON audit_history PIT filter (B1)  │
                     │  • compute_status from PIT-filtered audits   │
                     │  • drop status==retired; mark watch          │
                     │  • scope routing + per-scope caps + dedup    │
                     │  • attach _render_status + _render_reviews   │
                     │    as transient fields on each lesson view   │
                     └──────────────────────────────────────────────┘
```

In **live** mode, `pit_cutoff is None` → all lessons + all audits visible → status reflects full library state. The same-quarter guard still fires (compares ticker+quarter, not timestamps). Zero new code paths.

---

## 3. Goals and non-goals

### Goals

| # | Goal | How achieved |
|---|------|--------------|
| G1 | **Lessons are causal hypotheses, not memorized patterns** | Required `mechanism + applies_when + invalid_if + evidence_refs`; learner SKILL §9.1 enforces specificity bar + anti-template list + valid-lesson rubric + invalid-lesson signals (no concrete prose examples — principles only, to avoid LLM anchoring) |
| G1a | **Lessons are grounded in THIS quarter's specific reaction** (not historical pattern-matching, not financial maxims) | Critical Rule 11; `evidence_refs` MUST point to THIS learner run's evidence_ledger entries that DIRECTLY demonstrate the mechanism; Phase 2 explicit "what did THIS quarter teach?" probes |
| G2 | **Bad lessons retire automatically** | Status state machine; `misled` audits drive `active → watch → retired` |
| G3 | **Good lessons accrue trust visible to predictor** | `[reviews: Nh helped, Nm misled]` rendered inline; predictor weights by track record |
| G4 | **Refinement, not just replacement** | Learner can author refined version with `parent_id`; deterministic chain |
| G5 | **Three scopes routed correctly** + **scope-choice protocol** | Existing routing unchanged; learner SKILL §9.1 adds explicit scope-choice protocol (where does the mechanism live: company / sector / macro / cross_ticker); Phase 2 probes investigate at each scope |
| G6 | **Live = historical** | Same Python everywhere; only PIT plumbing differs; PIT correctness applies to BOTH lesson-level AND audit-level filters |
| G7 | **Production-grade with minimal moving parts** | Single new function + schema upgrades to existing files; no new agents/services/schedules |
| G8 | **Same-quarter self-leak prevented** | Explicit filter in `build_learning_context` |
| G9 | **Backtesting accuracy preserved** | Per-lesson audit_history filtered at render time prevents future-info leak (B1 fix) |
| G10 | **Recovery completeness** | Aggregator runs in BOTH success AND recovery paths (D18) |

### Non-goals (explicit)

- **NOT** building a new ML pipeline (no embeddings, no training jobs, no ranking model)
- **WIPE** existing lessons before v3 cutover (round 6 fresh-start; existing data is too thin to migrate; clean slate avoids legacy complexity)
- **NOT** validator-enforcing semantic content quality ("no thresholds without mechanism" — too brittle)
- **NOT** introducing a 4th status enum (round 6 fresh-start removed the legacy mechanism=null branch entirely; `active`/`watch`/`retired` is sufficient)
- **NOT** changing the predictor's output schema (predictor SKILL.md gets a 10-line addition; `prediction_result.v1` unchanged)
- **NOT** auto-aggregating multi-event audits across tickers (each audit is per-event)
- **NOT** storing status on disk (D17 — compute at read time; audit_history is the fact log)

---

## 4. Decisions locked

Every decision below is closed. The "why" is the rationale that will be load-bearing during implementation.

| # | Decision | Why |
|---|----------|-----|
| D1 | **Schema is `attribution_result.v3` only.** No v2 read-compat (fresh-start cutover; legacy data wiped) | Production hygiene; clean break |
| D2 | **Storage stays quarter-row-shaped on ticker.json**; lessons inside become structured dicts | ChatGPT correct: full flatten was over-aggressive. Context-Only block stays naturally per-quarter. Refinements live on auditing-quarter's row with `parent_id` link |
| D3 | **6-value review enum**: `helped / misled / outweighed / missed / neutral / unclear` | Distinguishes "lesson misled predictor" from "predictor failed to use a good lesson." Collapsing them would unfairly retire good lessons after a predictor mistake |
| D4 | **3-value action enum**: `keep / refine / retire` | Minimum viable for orthogonal directives — review answers "what happened," action answers "what to do" |
| D5 | **Validator enforces field existence + min length**, NOT semantic content | Semantic regex would be brittle; prompt enforces quality; audit feedback disciplines over time |
| D6 | **Conservative status thresholds**: 3+ misled in last 5 → retired; 2+ misled OR 2+ missed in last 5 → watch; outweighed never penalizes | Outweighed means "lesson was sound, other forces won." Penalizing it damages good lessons |
| ~~D7~~ | ~~Legacy lessons render with mechanism=null placeholder~~ | **WITHDRAWN** (round 6 fresh-start cutover): no legacy lessons exist; library is wiped before v3 cutover |
| D8 | **`lesson_audit[]` is uncapped — full coverage required (one entry per `lesson_labels[i]`)** | Capping audits forces incomplete coverage = lost signal. New-lesson caps stay 3/3/3 |
| D9 | **`data_lessons` stay as `list[str]`** | Data lessons are "what to fetch/weight," not market hypotheses; structure is overkill |
| D10 | **`lesson_id` = `sha256(normalized(lesson) + scope + str(routing_key))[:10]`** | Stable, reproducible, no UUID generation; collision-resistant; including scope+routing prevents cross-scope collision |
| D11 | **Field name: `lesson_audit`** (not `prior_lesson_reviews`) | Pairs cleanly with `audit_history` on the lesson row |
| ~~D12~~ | ~~Migration: backup-and-rewrite in place~~ | **WITHDRAWN** (round 6): wipe-and-init clean libraries on cutover. Existing data is too thin to be worth migrating; clean slate avoids legacy complexity |
| D13 | **PIT self-leak guard bundled in same commit set** (orchestrator gap, not strictly part of revamp) | Discovered during review; correctness-critical |
| D14 | **`invalid_if` field added** (in addition to `applies_when`) | Forces learner to name failure conditions explicitly |
| D15 | **Audit entries carry both `lesson_index` AND `lesson_text`** | Index for primary mapping, text for cross-validation defense in depth |
| D16 | **Audit entries require `evidence_refs: list[str]`** pointing into the learner's evidence_ledger; validator cross-checks IDs (B3) | Forces grounding: every verdict must cite specific evidence |
| **D17** | **Status is COMPUTED at read time, not stored on disk.** audit_history is the canonical fact log; status is a pure function of (audit_history, mechanism) at a given pit_cutoff | Resolves PIT-correctness automatically; eliminates dual-source-of-truth risk; replays at any past pit_cutoff produce the historically-correct status without storing snapshots |
| **D18** | **Aggregator runs in BOTH success AND recovery paths** | Recovery path (orchestrator:1142-1167) currently calls append_*_lesson then returns. Without aggregator hook, recovered runs leave audit_history un-updated. Closed-loop integrity requires both paths. |
| **D19** | **Orchestrator-level cross-file validation is REQUIRED, not optional.** After validate_attribution_result succeeds, the orchestrator asserts: `len(lesson_audit) == len(prediction.lesson_labels)`, each audit's `lesson_text` matches the bundle's body at `lesson_index`, `predictor_label` matches the prediction's label, `was_cited` matches `cites_lesson_indices`. Mismatch triggers the existing H2 informed-retry loop. | Hook validator is path-blind (stdlib-only, no prediction file access). Schema validation alone allows audits drifted from prediction reality. |
| D20 | **Renderer's `ordered_lesson_texts` contains LESSON BODY ONLY** (not mechanism/status decoration) | Predictor's T1 positional equality check (orchestrator:721-732) compares `lesson_labels[i].lesson_text` to expected body. Decoration must NOT bleed into the body. Predictor SKILL.md must instruct: "copy only the `Lesson:` body into lesson_text" |
| ~~D21~~ | ~~Legacy v2 learner outputs handled explicitly in recovery path~~ | **WITHDRAWN** (round 6): fresh-start cutover wipes existing `events/*/learning/result.json` files alongside library files. No v2 files exist post-cutover; recovery path only encounters v3 |
| **D22** | **Duplicate lesson_id assertion at every append/refinement**: scan target library file for the computed lesson_id; if it exists with DIFFERENT content (lesson body / mechanism / scope), raise. Identical content under same id is a no-op (idempotent). | At ~10^4 lessons in 16^10 keyspace, collision probability ~10^-4 — non-zero. Silent collision corrupts audit attribution. Cheap defensive check; loud fail beats silent corruption. |

---

## 5. Schema specs

### 5.1 `attribution_result.v3` — learner output

```json
{
  "schema_version": "attribution_result.v3",
  // ── existing v2 top-level fields unchanged ──

  "feedback": {
    // ── existing v2 unchanged ──
    "prediction_comparison": { ... },
    "what_worked": [ ... ],            // cap 2
    "what_failed": [ ... ],            // cap 3
    "why": "...",
    "data_lessons": ["...", "..."],     // cap 3, list[str] (D9)

    // ── CHANGED (v3): predictor_lessons becomes list[dict] ──
    "predictor_lessons": [              // cap 3
      {
        "lesson":        "<heuristic, 1-2 sentences>",
        "mechanism":     "<the causal chain explaining why this lesson worked in THIS event>",
        "applies_when":  "<bundle preconditions for the lesson to fire>",
        "invalid_if":    "<conditions that nullify the lesson>",
        "evidence_refs": ["E2", "E5"]   // NEW (N3) — pointers into THIS learner's evidence_ledger
      }
    ]
  },

  "global_observations": [              // cap 3
    {
      "scope": "sector",                // sector | macro | cross_ticker
      "target_sector": "Technology",    // scope-conditional shape (unchanged)
      // OR "related_tickers": ["A","B"] for cross_ticker
      // OR neither for macro
      "lesson":        "...",
      "mechanism":     "...",
      "applies_when":  "...",
      "invalid_if":    "...",
      "evidence_refs": ["E3", "E7"]     // NEW (N3)
    }
  ],

  // ── NEW REQUIRED FIELD when prediction had non-empty lesson_labels ──
  "lesson_audit": [
    {
      "lesson_index":     0,                    // 0-based position in prediction.lesson_labels
      "lesson_text":      "<verbatim, for cross-validation>",
      "predictor_label":  "confirmed",          // copied from prediction.lesson_labels[i].label
      "was_cited":        true,                 // was idx in any cites_lesson_indices?
      "review":           "helped",             // 6-value enum, see §5.3
      "action":           "keep",               // 3-value enum, see §5.4
      "comment":          "<1 sentence with evidence>",
      "evidence_refs":    ["E3", "E7"],         // pointers into THIS learner's evidence_ledger; validator cross-checks
      "replacement_lesson": null | {            // present iff action == "refine"
        "lesson":        "...",
        "mechanism":     "...",
        "applies_when":  "...",
        "invalid_if":    "...",
        "evidence_refs": ["E2"]
      }
    }
    // ... exactly len(prediction.lesson_labels) entries (D8 full coverage)
  ]
}
```

### 5.2 Lesson row (storage — flat provenance, two variants)

**Round 7 design correction**: provenance is **FLAT**, matching the existing `append_global_lessons` shape (orchestrator:1414-1430). The earlier nested `source: {...}` block in this section was inconsistent with the existing flat shape and with §7.5.1's same-quarter guard (which reads `e.get("source_ticker")`). Removed.

There are TWO row shapes — ticker-scope lessons live INSIDE quarter rows and inherit provenance from the outer row; global-scope entries are top-level rows in `global.json` and carry their own flat provenance.

**(A) Ticker-scope lesson dict — lives inside `ticker.json::lessons[i].predictor_lessons[j]`:**

```json
{
  "lesson_id":      "lsn_<10-char-hash>",
  "lesson":         "...",
  "mechanism":      "...",
  "applies_when":   "...",
  "invalid_if":     "...",
  "evidence_refs":  [ "...", "..." ],
  "scope":          "ticker",
  "routing_key":    "AVGO",
  "audit_history":  [ ... ],                 // see audit-entry shape below
  "parent_id":      null | "<lesson_id>"
}
// NO per-lesson source.* / created_at / source_pit_cutoff fields —
// these inherit from the outer quarter row (which already carries
// quarter_label, attributed_at, source_filed_8k, source_pit_cutoff,
// actual_daily_pct, predicted_direction, direction_correct,
// primary_driver_category, primary_driver_summary, etc.)
```

**(B) Global-scope lesson entry — top-level in `global.json::entries[]`:**

```json
{
  "lesson_id":      "lsn_<10-char-hash>",
  "lesson":         "...",
  "mechanism":      "...",
  "applies_when":   "...",
  "invalid_if":     "...",
  "evidence_refs":  [ "...", "..." ],
  "scope":          "sector|macro|cross_ticker",
  "routing_key":    "Technology" | null | ["A","B"],   // sorted tuple for cross_ticker

  // Scope-conditional routing field (kept at top level — used by existing
  // build_learning_context routing logic; do not move):
  "target_sector":  "Technology",            // present only when scope="sector"
  // OR "related_tickers": ["AVGO","QCOM"],  // present only when scope="cross_ticker"
  // OR neither for scope="macro"

  // FLAT provenance (matches existing append_global_lessons shape):
  "source_ticker":      "AVGO",
  "source_sector":      "Technology",        // audit-only, NOT routing
  "quarter_label":      "Q3_FY2023",
  "attributed_at":      "<ISO ts>",
  "source_filed_8k":    "<ISO ts>",
  "source_pit_cutoff":  "<ISO ts>" | null,

  // State:
  "audit_history":      [ ... ],             // see audit-entry shape below
  "parent_id":          null | "<lesson_id>"
}
```

**(C) Audit-history entry shape (same in both A and B):**

```json
{
  "auditor_ticker":           "AVGO",
  "auditor_quarter_label":    "Q4_FY2023",
  "audited_at":               "<ISO ts>",
  "audit_pit_cutoff":         "<ISO ts>" | null,    // load-bearing for B1 PIT filter
  "predictor_label_at_audit": "confirmed",
  "was_cited":                true,
  "review":                   "helped",
  "action":                   "keep",
  "comment":                  "...",
  "evidence_refs":            ["E3"]
}
// append-only; no cap (N1)
// NOTE: lesson_text from learner output is NOT persisted here —
// it's used only at validation time for D19 cross-file check
```

**Note (D17)**: `status`, `retired_reason` are **NOT stored**. They are computed at read time by `compute_status(lesson)` after `build_learning_context` PIT-filters the audit_history.

### 5.3 `review` enum (D3 — 6 values)

| Value | Meaning | Status impact |
|-------|---------|---------------|
| `helped` | Predictor used the lesson AND outcome aligned | Reinforces (counter +1) |
| `misled` | Predictor used the lesson AND outcome wrong because lesson's reasoning was bad | Drives toward `watch` / `retired` |
| `outweighed` | Predictor used the lesson; mechanism was real; other forces dominated | Neutral — lesson logic was sound, no penalty (D6) |
| `missed` | Predictor labeled `irrelevant` / didn't cite, but hindsight shows lesson was applicable | Drives toward `watch` (lesson trigger may be too narrow); does NOT retire (predictor's labeling failure, not lesson failure) |
| `neutral` | Predictor's label was correct (e.g., `irrelevant` and lesson really didn't apply); no impact on call | No status pressure |
| `unclear` | Hindsight cannot isolate the effect | No status pressure |

### 5.4 `action` enum (D4 — 3 values)

| Value | Effect |
|-------|--------|
| `keep` | No mutation beyond appending the audit entry |
| `refine` | `replacement_lesson` MUST be present. Aggregator registers replacement as new lesson with `parent_id = <old_lesson_id>` in the auditor's quarter row (or as a new global entry). compute_status returns `retired` for the parent because the audit_history entry that triggered refine is permanent. |
| `retire` | Audit entry's `action="retire"` is permanent in audit_history. compute_status returns `retired` whenever the action="retire" entry is in PIT-visible scope. |

---

## 6. Storage layout

### 6.1 `learnings/ticker/{TICKER}.json`

```json
{
  "schema_version": "ticker_lessons.v2",
  "ticker": "AVGO",
  "updated_at": "<ISO ts>",
  "lessons": [
    {
      // per-quarter row — OUTER SHAPE UNCHANGED from v1
      "quarter_label": "Q3_FY2023",
      "attributed_at": "...",
      "source_filed_8k": "...",
      "source_pit_cutoff": "...",
      "direction_correct": true,
      "actual_daily_pct": 5.54,
      "predicted_direction": "no_call",
      "predicted_confidence_score": 25,
      "primary_driver_summary": "...",
      "primary_driver_category": "...",
      "what_worked": [...],
      "what_failed": [...],
      "data_lessons": [...],          // list[str]
      "why": "...",

      // ── CHANGED: predictor_lessons is now list[<lesson row dict>] ──
      "predictor_lessons": [
        { /* lesson row per §5.2 — NO stored status field */ }
      ]
    }
  ]
}
```

### 6.2 `learnings/global.json`

```json
{
  "schema_version": "global_lessons.v2",
  "updated_at": "<ISO ts>",
  "entries": [
    { /* lesson row per §5.2; routing fields at top level — NO stored status field */ }
  ]
}
```

### 6.3 Append-function modifications (round 6 explicit spec)

`append_ticker_lesson` and `append_global_lessons` (orchestrator:1317, 1371) are modified to write the structured lesson-row schema (§5.2). Per-lesson stamping responsibility is **Python's, not the LLM's** — the learner emits content fields only (lesson, mechanism, applies_when, invalid_if, evidence_refs); Python stamps identity + provenance + initial state.

**`append_ticker_lesson(ticker, attribution_result)` — for each `feedback.predictor_lessons[i]`:**

The OUTER quarter row already carries flat provenance fields (orchestrator:1340-1366 retains its existing shape: `quarter_label`, `attributed_at`, `source_filed_8k`, `source_pit_cutoff`, `actual_daily_pct`, `predicted_direction`, `direction_correct`, `primary_driver_summary`, `primary_driver_category`, `what_worked`, `what_failed`, `data_lessons`, `why`). The lesson dict inside `predictor_lessons[]` only carries identity + content + state — no duplicated provenance.

For each `lesson_dict` from learner's `feedback.predictor_lessons[]`:
1. Compute `routing_key = ticker.upper()`
2. Compute `lesson_id = compute_lesson_id(lesson_dict["lesson"], scope="ticker", routing_key)`
3. Run `assert_no_id_collision(ticker.json, "ticker", lesson_id, lesson_dict)` — D22 site #1
4. Build the per-lesson dict by stamping ONLY identity + content + state:
   - `lesson_id` (computed), `scope: "ticker"`, `routing_key: ticker`
   - Content verbatim: `lesson, mechanism, applies_when, invalid_if, evidence_refs`
   - `audit_history: []`, `parent_id: null`
   - **No source.\* fields, no created_at, no source_pit_cutoff** — inherited from outer quarter row
5. Append to the appropriate quarter row's `predictor_lessons[]` array.

**`append_global_lessons(attribution_result)` — for each `global_observations[i]`:**

Each entry in `global.json::entries[]` is a stand-alone row — provenance is flat on the row (matches existing orchestrator:1414-1430 shape).

For each `obs` from learner's `global_observations[]`:
1. Compute `routing_key = _routing_key_from_source(obs.scope, obs)` (see §7.1; non-ticker scopes don't need ticker_hint)
2. Compute `lesson_id = compute_lesson_id(obs["lesson"], obs["scope"], routing_key)`
3. Run `assert_no_id_collision(global.json, obs["scope"], lesson_id, full_entry)` — D22 site #2
4. Build the entry by stamping (flat shape):
   - Identity: `lesson_id`, `scope`, `routing_key`
   - Content: `lesson, mechanism, applies_when, invalid_if, evidence_refs`
   - Scope-conditional routing field preserved at top level: `target_sector` (sector scope) OR `related_tickers` (cross_ticker scope) OR neither (macro)
   - Flat provenance from `attribution_result`: `source_ticker = attribution_result.ticker.upper()`, `source_sector = _lookup_company_sector(source_ticker)`, `quarter_label`, `attributed_at`, `source_filed_8k`, `source_pit_cutoff`
   - State: `audit_history: []`, `parent_id: null`
5. Upsert into `entries[]` under existing flock pattern (orchestrator:1438) using `(source_ticker, quarter_label, lesson_id)` as upsert key (extends existing per-event upsert by one component for stable lesson identity).

The learner's output never carries `lesson_id` / `audit_history` / `parent_id` — these are Python-owned. If a learner output happens to include them, the validator does NOT reject (extra fields permitted), but Python ignores them and re-stamps from authoritative sources.

### 6.4 Why the quarter-row shape on ticker.json (D2)

Full flatten of ticker.json into lesson-centric rows breaks too many existing assumptions:
- `iter_labeled_lessons` walks per-quarter then per-lesson — natural fit
- Renderer's Context-Only block is rendered ONCE per quarter using the quarter row's outer fields
- `_decorate_with_learner_paths` iterates per quarter
- Validator's positional equality with renderer is unchanged

Structured-lesson-dict-inside-quarter-row gets us per-lesson health WITHOUT touching iter_labeled_lessons signature, renderer Context-Only block, or learner-paths decorator.

---

## 7. Algorithms

### 7.1 Lesson identity (D10)

```python
import hashlib

def compute_lesson_id(lesson_text: str, scope: str, routing_key) -> str:
    """Stable lesson id derived from normalized content + scope + routing.
    
    routing_key shape per scope:
      - ticker:       ticker symbol "AVGO"
      - sector:       canonical sector "Technology"
      - macro:        None
      - cross_ticker: tuple/sorted-list of tickers ("AVGO", "QCOM")
    """
    normalized_text = " ".join((lesson_text or "").strip().split()).lower()
    if isinstance(routing_key, (list, tuple)):
        routing_repr = ",".join(sorted(str(t).upper() for t in routing_key))
    else:
        routing_repr = str(routing_key) if routing_key is not None else ""
    payload = f"{normalized_text}|{scope}|{routing_repr}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:10]
    return f"lsn_{digest}"


def assert_no_id_collision(library_path: Path, scope: str, lesson_id: str,
                            new_content: dict) -> None:
    """D22: collision-detection assertion. Called at every append/refine.
    
    Loads target library file. For each existing lesson_id matching `lesson_id`:
      - If the existing lesson's normalized (lesson, mechanism, scope, routing_key)
        matches new_content → idempotent no-op (legitimate same lesson re-emitted).
      - Otherwise → raise DuplicateLessonIdError with both contents for inspection.
    
    Loud failure beats silent collision. Cheap (linear scan over O(N) lessons).
    """
    if not library_path.exists():
        return
    data = json.loads(library_path.read_text())
    candidates = []
    if scope == "ticker":
        for q_row in data.get("lessons", []):
            for pl in q_row.get("predictor_lessons", []):
                if isinstance(pl, dict) and pl.get("lesson_id") == lesson_id:
                    candidates.append(pl)
    else:
        for entry in data.get("entries", []):
            if entry.get("lesson_id") == lesson_id:
                candidates.append(entry)
    for existing in candidates:
        if not _content_matches(existing, new_content):
            raise DuplicateLessonIdError(
                f"lesson_id {lesson_id} collision in {library_path}: "
                f"existing content differs from new_content"
            )
```

Properties:
- Same lesson body + scope + routing → same id (idempotent under re-runs)
- Refinement (different text) → different id (chain via `parent_id`)
- Cross-scope same-text → different id (scope is in the hash)
- 10-char prefix → ~10^12 keyspace; collision rare (~10^-4 at 10^4 lessons), but D22 assertion makes it loud rather than silent

**`_routing_key_from_source(scope, source_entry)` — explicit helper definition:**

```python
def _routing_key_from_source(scope: str, source_entry: dict, *, ticker_hint: str | None = None):
    """Derive routing_key from a global.json entry OR a ticker.json quarter row context.
    
    Callers MUST pass ticker_hint when scope='ticker' — ticker.json quarter rows
    don't carry per-lesson ticker (the file itself is per-ticker). Do NOT infer
    ticker from quarter_label or any other quarter-row field.
    """
    if scope == "ticker":
        if not ticker_hint:
            raise ValueError("ticker_hint required for scope='ticker'")
        return ticker_hint.upper()
    if scope == "sector":
        return source_entry.get("target_sector")  # canonical sector string
    if scope == "macro":
        return None
    if scope == "cross_ticker":
        rt = source_entry.get("related_tickers") or []
        return tuple(sorted(t.upper() for t in rt))  # sorted tuple for stable hash
    raise ValueError(f"unknown scope: {scope}")
```

**D22 collision-check insertion sites — exactly three:**
1. `append_ticker_lesson` — when stamping a new ticker-scope lesson dict (§6.3)
2. `append_global_lessons` — when stamping a new global entry (sector/macro/cross_ticker) (§6.3)
3. `_register_replacement` — when registering a refined replacement lesson (§7.2)

Idempotency rule (uniform across all 3 sites):
- Existing `lesson_id` with **identical content** (lesson + mechanism + applies_when + invalid_if + scope + routing_key) → no-op (silent return; aggregator may safely re-run)
- Existing `lesson_id` with **different content** → raise `DuplicateLessonIdError` (loud halt; investigate before retry)

### 7.2 Aggregator (the only state-mutating component)

**D18**: runs in BOTH the success path (orchestrator:1281-ish, after `append_global_lessons`) AND the recovery path (orchestrator:1162-1167, after the same appends).

Pure Python; deterministic; idempotent under re-runs. Writes only to `audit_history` (append-only) and to library state for refinements (new lesson registration). Does NOT write a `status` field to disk (D17).

```python
def aggregate_lesson_audits(
    *,
    learning_payload: dict,        # learning/result.json (just written or recovered)
    prediction_payload: dict,      # prediction/result.json
    bundle: dict,                  # context_bundle.json (the bundle the predictor saw)
    auditor_ticker: str,
    auditor_quarter_label: str,
    audit_pit_cutoff: str | None,  # learner's pit_cutoff (None for live)
    learnings_dir: Path = LEARNINGS_DIR,
) -> None:
    """Apply the learner's audits to library state.
    
    Steps:
      1. Walk bundle.learning_context via iter_labeled_lessons → ordered list
         [(n, scope, source_entry, body), ...] in canonical render order.
      2. For each lesson_audit[i], use lesson_index to find (scope, source_entry, body).
      3. Compute lesson_id from (body, scope, routing_key derived from source_entry).
      4. Locate the matching lesson dict by lesson_id within the appropriate library file:
           - For scope=ticker: scan source_entry["predictor_lessons"] for the dict
             with matching lesson_id; this is the lesson dict to update.
           - For scope=sector|macro|cross_ticker: scan global.json entries for
             matching lesson_id.
         (The iterator yields the BODY; the aggregator does id-based lookup to
         resolve to the exact lesson dict. This avoids changing the iterator
         signature, which is shared by renderer + validator + U67 catalog.)
      5. Append the audit entry to that lesson's audit_history (upsert by
         (auditor_ticker, auditor_quarter_label) — re-runs replace, not duplicate).
      6. Handle action="refine": register replacement_lesson as a NEW lesson
         dict in the auditor's CURRENT quarter row (with parent_id link to the
         retired lesson). The retire is implicit — compute_status sees the
         action="retire"-equivalent state via the parent's audit_history entry
         (which carries action="refine" and replacement_lesson; compute_status
         treats action in {"refine", "retire"} as terminal).
      7. Handle action="retire": the audit entry's action="retire" is permanent
         in audit_history; compute_status sees it.
      8. Write all touched library files atomically (existing _atomic_write_json
         + flock for global.json).
    
    Defensive behavior:
      - lesson_index out of range → log warning, skip that audit
      - lesson_text mismatch with body at index → log warning, prefer index match
      - replacement_lesson missing on action=refine → log error, treat as keep
      - lesson_id not found in library → log error, skip (drift detection)
    """
    audits = learning_payload.get("lesson_audit") or []
    if not audits:
        return  # first-prediction or no labels

    learning_ctx = bundle.get("learning_context") or {}
    indexed = list(iter_labeled_lessons(learning_ctx))
    labels = prediction_payload.get("lesson_labels") or []

    cited = set()
    for kd in prediction_payload.get("key_drivers") or []:
        cited.update(kd.get("cites_lesson_indices") or [])

    for audit in audits:
        idx = audit["lesson_index"]
        if not (0 <= idx < len(indexed)) or not (0 <= idx < len(labels)):
            log.warning("aggregator: lesson_index=%d out of range; skipping", idx)
            continue
        n, scope, source_entry, body = indexed[idx]

        # D15: lesson_text cross-check (defensive)
        if _normalize_lesson_text(audit.get("lesson_text", "")) != \
           _normalize_lesson_text(body):
            log.warning(
                "aggregator: lesson_text drift at index=%d; using index match", idx
            )

        # Round 7 footgun fix: ticker_hint required when scope='ticker' (helper raises otherwise).
        # auditor_ticker is the correct hint because ticker-scope lessons are only
        # rendered to (and only audited by) the SAME ticker's predictor.
        if scope == "ticker":
            routing_key = _routing_key_from_source(scope, source_entry, ticker_hint=auditor_ticker)
        else:
            routing_key = _routing_key_from_source(scope, source_entry)
        lesson_id = compute_lesson_id(body, scope, routing_key)

        audit_entry = {
            "auditor_ticker":          auditor_ticker,
            "auditor_quarter_label":   auditor_quarter_label,
            "audited_at":              learning_payload.get("attributed_at"),
            "audit_pit_cutoff":        audit_pit_cutoff,
            "predictor_label_at_audit": labels[idx]["label"],
            "was_cited":               (idx in cited),
            "review":                  audit["review"],
            "action":                  audit["action"],
            "comment":                 audit["comment"],
            "evidence_refs":           audit.get("evidence_refs", []),
        }

        # Apply audit + handle refinement.
        # Round 9 fix: aggregator must derive helper inputs to match the
        # canonical signatures in §7.2.1 — pass explicit paths and
        # quarter_label, NOT the in-memory bundle quarter-row dict.
        # Round 11 fix (E31 atomicity): for global+refine, the audit append
        # AND the replacement insert MUST happen under a SINGLE flock on
        # global.lock. Achieved by routing both writes through
        # _register_replacement (which handles audit append inline for global
        # scope) when action == "refine"; the separate _apply_audit_global
        # call is skipped in that branch.
        is_refine = (audit["action"] == "refine"
                     and isinstance(audit.get("replacement_lesson"), dict))
        if scope == "ticker":
            ticker_path = learnings_dir / "ticker" / f"{auditor_ticker}.json"
            source_quarter_label = source_entry.get("quarter_label")
            if not source_quarter_label:
                log.error(
                    "aggregator: ticker-scope lesson missing quarter_label "
                    "in bundle; cannot locate target row. lesson_id=%s",
                    lesson_id,
                )
                continue
            # Ticker-scope: ticker.json has no concurrent writers (single-ticker
            # sequential per orchestrator convention), so two sequential opens
            # are acceptable. Audit append happens first; refinement second.
            _apply_audit_ticker(ticker_path, source_quarter_label, lesson_id, audit_entry)
            if is_refine:
                _register_replacement(
                    learnings_dir,
                    parent_lesson_id=lesson_id,
                    parent_scope=scope,
                    parent_source_entry=source_entry,
                    replacement=audit["replacement_lesson"],
                    auditor_ticker=auditor_ticker,
                    auditor_quarter_label=auditor_quarter_label,
                    audit_pit_cutoff=audit_pit_cutoff,
                    learning_payload=learning_payload,
                    audit_entry=None,   # ticker path: audit already applied above
                )
        else:
            global_path = learnings_dir / "global.json"
            if is_refine:
                # Atomic global+refine path: audit append + new-entry insert
                # under one flock. _register_replacement handles BOTH writes
                # for global scope when audit_entry is provided.
                _register_replacement(
                    learnings_dir,
                    parent_lesson_id=lesson_id,
                    parent_scope=scope,
                    parent_source_entry=source_entry,
                    replacement=audit["replacement_lesson"],
                    auditor_ticker=auditor_ticker,
                    auditor_quarter_label=auditor_quarter_label,
                    audit_pit_cutoff=audit_pit_cutoff,
                    learning_payload=learning_payload,
                    audit_entry=audit_entry,   # global path: bundle audit append
                )
            else:
                # No refinement: simple audit append (own flock acquisition)
                _apply_audit_global(global_path, lesson_id, audit_entry)
        # action="retire" is encoded in the audit_entry itself (already appended);
        # compute_status reads it. No additional state mutation needed.
```

**Idempotency**: re-running with the same `(auditor_ticker, auditor_quarter_label)` upserts each audit entry (replaces, not duplicates). Refinement re-runs: the new lesson's id is computed from the replacement_lesson's normalized text — same input → same id → upsert by id (no duplicate registration).

**Concurrency**: ticker.json sequential per ticker; global.json uses existing flock (orchestrator:1438).

**Insertion points (D18)**:
- Success path: orchestrator post-success, after `append_ticker_lesson` + `append_global_lessons` (existing line ~1281). **Round 9 correction**: the existing success-path code only passes PATHS to the SDK (orchestrator:1199-1200) and does NOT load `prediction/result.json` or `context_bundle.json` as JSON. The aggregator + D19 must explicitly load both before invocation:
  ```python
  # Success path: load siblings before D19 + aggregator
  pred_path = attr_paths["prediction_result_path"]
  bundle_path = attr_paths["context_bundle_path"]
  try:
      prediction_payload = json.loads(pred_path.read_text(encoding="utf-8"))
      bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError) as e:
      log.error("success-path aggregator: cannot load sibling for %s %s: %s",
                ticker, ql, e)
      return None, LearnerOutcome.FAILED_VALIDATION
  ```
- Recovery path: orchestrator:1162-1166, after the same calls, BEFORE `return existing, LearnerOutcome.RECOVERED`. **The recovery path must explicitly load the sibling files** — they're not loaded today since recovery only re-appends. Specifically:
  ```python
  # Round 6: recovery must load siblings before D19 + aggregator
  pred_path = attr_paths["prediction_result_path"]
  bundle_path = attr_paths["context_bundle_path"]
  if not pred_path.is_file() or not bundle_path.is_file():
      log.error("recovery aggregator: missing sibling file(s) for %s %s", ticker, ql)
      return None, LearnerOutcome.FAILED_RECOVERY_APPEND
  try:
      prediction_payload = json.loads(pred_path.read_text(encoding="utf-8"))
      bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError) as e:
      log.error("recovery aggregator: corrupt sibling for %s %s: %s", ticker, ql, e)
      return None, LearnerOutcome.FAILED_RECOVERY_APPEND
  ```
  Wrap aggregator + cross-file check in same try/except as the appends; on any failure return `FAILED_RECOVERY_APPEND` (do NOT silently skip — silent skip would leave audit_history un-updated for legitimate recovered runs).

**Aggregator invocation (v3-only, round 6 fresh-start)** — both insertion points:

```python
# At each insertion site (success path AND recovery path):
sv = learning_payload.get("schema_version")
if sv != "attribution_result.v3":
    log.error(f"unsupported schema_version in learner result: {sv} — only v3 accepted")
    return None, LearnerOutcome.FAILED_VALIDATION

# v3 path: cross-file validation + aggregator
cross_errors = _validate_audit_against_prediction(
    learning_payload, prediction_payload, bundle,
)
if cross_errors:
    # Trigger H2 informed-retry on success path; abort on recovery
    ...
aggregate_lesson_audits(
    learning_payload=learning_payload,
    prediction_payload=prediction_payload,
    bundle=bundle,
    auditor_ticker=ticker,
    auditor_quarter_label=quarter_info["quarter_label"],
    audit_pit_cutoff=pit_cutoff,  # learner's pit_cutoff (None for live)
)
```

Single path; non-v3 fails loudly. No legacy dispatch (round 6 fresh-start cutover wiped pre-v3 files).

**`_register_replacement` — explicit definition:**

```python
def _register_replacement(
    learnings_dir: Path,
    *,
    parent_lesson_id: str,
    parent_scope: str,
    parent_source_entry: dict,    # the bundle entry from iter_labeled_lessons,
                                  # used ONLY to inherit routing_key
    replacement: dict,            # {lesson, mechanism, applies_when, invalid_if, evidence_refs}
    auditor_ticker: str,
    auditor_quarter_label: str,
    audit_pit_cutoff: str | None,
    learning_payload: dict,       # for source.* stamping
    audit_entry: dict | None,     # round 11: required for global scope (E31 atomicity);
                                  # None for ticker scope (audit already applied upstream)
) -> str:
    """Refinement registers a NEW lesson row that inherits parent's scope +
    routing_key. Provenance fields are flat (matching the storage convention).
    Returns the new lesson_id.
    
    Constraints:
      - Refinement does NOT change scope. If the learner needs to change scope,
        they must retire the parent AND emit a SEPARATE new lesson at the new
        scope normally. This prevents scope drift via refinement.
      - Ticker-scope routing: auditor_ticker is AUTHORITATIVE
        (round 8/9 design). Ticker-scope lessons live at file-system level in
        learnings/ticker/{auditor_ticker}.json by construction; no runtime
        invariant check or hard-error. If a future bundle-assembly bug ever
        cross-contaminates ticker libraries, the failure surfaces elsewhere
        (T1 positional check, render-order tests).
      - Atomicity (round 11 — E31): for global scope, the parent's audit-append
        AND the replacement-entry insert MUST happen under a SINGLE flock
        acquisition on global.lock. The aggregator passes `audit_entry` to
        this function for global+refine; the function appends it to the
        parent's audit_history inline, then inserts the new entry, all under
        one lock. For ticker scope, audit_entry is None (already applied
        upstream by _apply_audit_ticker — ticker.json has no concurrent
        writers, so two sequential opens are acceptable).
    """
    # 1. Compute routing_key. For ticker scope, auditor_ticker is AUTHORITATIVE
    # (round 8 design choice — removes the fake-invariant footgun).
    #
    # Justification: ticker-scope lessons live in learnings/ticker/{TICKER}.json
    # where {TICKER} is the FILENAME. build_learning_context loads ticker_lessons
    # from learnings/ticker/{auditor_ticker}.json (orchestrator:1635). So
    # ticker-scope lessons in the bundle are by file-system construction owned
    # by auditor_ticker. parent_source_entry (a quarter-row context) does not
    # carry per-row source_ticker, and reading ticker.json's filename through
    # the bundle would be a layered lookup with no value.
    #
    # If a future bug allowed cross-ticker contamination (e.g., bundle assembly
    # mixed multiple tickers' libraries), the failure surface would be elsewhere
    # (T1 positional check, render-order tests). No need to defend it here.
    if parent_scope == "ticker":
        routing_key = auditor_ticker.upper()
    else:
        routing_key = _routing_key_from_source(parent_scope, parent_source_entry)
    
    # 2. Compute new lesson_id (different text → different hash)
    new_id = compute_lesson_id(replacement["lesson"], parent_scope, routing_key)
    
    # 3. Build the new lesson row (flat shape per §5.2)
    if parent_scope == "ticker":
        # Lesson dict goes inside the auditor's quarter row in ticker.json.
        # Provenance comes from the outer quarter row (already stamped by
        # append_ticker_lesson on this auditor's quarter), not duplicated here.
        new_row = {
            "lesson_id":      new_id,
            "lesson":         replacement["lesson"],
            "mechanism":      replacement["mechanism"],
            "applies_when":   replacement["applies_when"],
            "invalid_if":     replacement["invalid_if"],
            "evidence_refs":  replacement["evidence_refs"],
            "scope":          "ticker",
            "routing_key":    routing_key,
            "audit_history":  [],
            "parent_id":      parent_lesson_id,
        }
    else:
        # Global entry — flat provenance from auditor event
        ar = learning_payload.get("actual_return") or {}
        pc = (learning_payload.get("feedback") or {}).get("prediction_comparison") or {}
        pd = learning_payload.get("primary_driver") or {}
        new_row = {
            "lesson_id":      new_id,
            "lesson":         replacement["lesson"],
            "mechanism":      replacement["mechanism"],
            "applies_when":   replacement["applies_when"],
            "invalid_if":     replacement["invalid_if"],
            "evidence_refs":  replacement["evidence_refs"],
            "scope":          parent_scope,
            "routing_key":    routing_key,
            # Scope-conditional routing field — inherited from parent
            **({"target_sector": parent_source_entry["target_sector"]}
               if parent_scope == "sector" else {}),
            **({"related_tickers": parent_source_entry["related_tickers"]}
               if parent_scope == "cross_ticker" else {}),
            # Flat provenance: AUDITOR event
            "source_ticker":      auditor_ticker.upper(),
            "source_sector":      _lookup_company_sector(auditor_ticker),
            "quarter_label":      auditor_quarter_label,
            "attributed_at":      learning_payload.get("attributed_at"),
            "source_filed_8k":    learning_payload.get("filed_8k"),
            "source_pit_cutoff":  audit_pit_cutoff,
            # State
            "audit_history":      [],
            "parent_id":          parent_lesson_id,
        }
    
    # 4. D22 collision check (insertion site #3)
    if parent_scope == "ticker":
        target_path = learnings_dir / "ticker" / f"{routing_key}.json"
    else:
        target_path = learnings_dir / "global.json"
    assert_no_id_collision(target_path, parent_scope, new_id, new_row)
    
    # 5. Persist
    if parent_scope == "ticker":
        # Ticker scope: ticker.json has no concurrent writers; audit_entry was
        # already applied upstream by _apply_audit_ticker. Just append the new
        # row to the AUDITOR's quarter row.
        assert audit_entry is None, "ticker-scope: audit already applied upstream"
        _append_lesson_row_to_ticker_quarter(target_path, auditor_quarter_label, new_row)
    else:
        # Global scope (round 11 E31 atomicity): single flock acquisition for
        # parent's audit_history append + new entry insert.
        assert audit_entry is not None, "global-scope: aggregator must pass audit_entry"
        _apply_audit_and_append_global_atomic(
            target_path, parent_lesson_id, audit_entry, new_row,
        )
    
    return new_id
```

The parent lesson is automatically rendered as `retired` by `compute_status` because its `audit_history` will contain the `action="refine"` entry (atomically appended in the same flock as the new entry insert).

### 7.2.1 Helper-function contracts (round 7 explicit specs)

These helpers are referenced by the aggregator + `_register_replacement` + `append_*_lesson`. Pseudocode is intentionally minimal — focus is on inputs, upsert key, locking, failure mode.

| Helper | Inputs | Upsert key | Locking | Failure |
|---|---|---|---|---|
| `_apply_audit_ticker(ticker_path, source_quarter_label, lesson_id, audit_entry)` | ticker.json path; the prior quarter the lesson was created in (= `source_quarter_label`); lesson_id; audit_entry. **Lookup tuple = (`source_quarter_label`, `lesson_id`)** — D22 guarantees lesson_id is unique within a quarter row, so this tuple is exact-match. | Replace existing entry where `(auditor_ticker, auditor_quarter_label)` matches inside the matched lesson's audit_history; else append | None — single-ticker sequential per orchestrator (existing convention) | Raise if ticker.json missing/corrupt OR target quarter row OR target lesson_id not found |
| `_apply_audit_global(global_path, lesson_id, audit_entry)` | global.json path; lesson_id; audit_entry. Used for non-refine audits only. | Replace existing entry where `(auditor_ticker, auditor_quarter_label)` matches inside the matched lesson's audit_history; else append | `fcntl.flock` on `global.lock` (existing pattern, orchestrator:1438) | Raise if global.json missing/corrupt OR lesson_id not found |
| `_apply_audit_and_append_global_atomic(global_path, parent_lesson_id, audit_entry, new_entry)` (round 11 — E31) | global.json path; parent's lesson_id; audit_entry to append on parent; new replacement entry to insert | Two writes under SINGLE flock: (1) append audit_entry to parent's audit_history (with same upsert-by-`(auditor_ticker, auditor_quarter_label)` rule); (2) append new_entry to entries[]; then atomic replace | `fcntl.flock` on `global.lock` — acquired ONCE, released after both writes complete | Raise if global.json missing/corrupt OR parent_lesson_id not found OR new_entry's lesson_id collides (D22) |
| `_append_lesson_row_to_ticker_quarter(ticker_path, quarter_label, new_row)` | ticker.json path; target quarter (auditor's quarter for refinements; lesson's own quarter for fresh appends); new lesson dict | Append to that quarter row's `predictor_lessons[]`. Quarter row created if missing, with empty provenance fields stamped by caller's outer flow | None — sequential per ticker | Raise if ticker.json malformed |
| `_append_lesson_row_to_global(global_path, new_entry)` | global.json path; new entry | Append to `entries[]` (lesson_id collision already checked upstream by D22) | `fcntl.flock` on `global.lock` | Raise if global.json malformed |
| `_content_matches(existing_lesson_dict, new_content_dict)` | two dicts | n/a — pure compare | n/a | Returns bool. True iff `_normalize_lesson_text(lesson)` matches AND `mechanism` matches AND `applies_when` matches AND `invalid_if` matches AND `scope` equals AND `routing_key` equals (after normalizing routing_key list to sorted tuple). Used by `assert_no_id_collision` |

**Implementation rule — empty-`predictor_lessons` + ticker-scope refine.** When the auditor emits `feedback.predictor_lessons: []` but a ticker-scope `lesson_audit[i].action == "refine"`, `append_ticker_lesson` does not create the auditor's quarter row (no new lessons to attach). The aggregator's call to `_append_lesson_row_to_ticker_quarter` must then **create the quarter row from `learning_payload` using the same outer fields as `append_ticker_lesson` (orchestrator:1340-1366)** — `quarter_label`, `attributed_at`, `source_filed_8k`, `source_pit_cutoff`, `direction_correct`, `actual_daily_pct`, `predicted_direction`, `predicted_confidence_score`, `primary_driver_summary`, `primary_driver_category`, `what_worked`, `what_failed`, `data_lessons`, `why` — and then insert the replacement lesson into the freshly stamped row. Required fixture in `test_aggregate_lesson_audits.py`: `predictor_lessons: []` + one `lesson_audit[*].action == "refine"` on a ticker-scope parent → quarter row created, replacement registered with `parent_id`, parent's `audit_history` carries the `action="refine"` entry.

### 7.3 Status state machine (D6 + D17 + B2 fix — pure function)

```python
from collections import Counter

_STATUS_WINDOW = 5
_RETIRE_MISLED_THRESHOLD = 3
_WATCH_MISLED_THRESHOLD = 2
_WATCH_MISSED_THRESHOLD = 2

def compute_status(lesson: dict) -> str:
    """Pure function over lesson dict. Caller must pre-filter audit_history
    by audit_pit_cutoff <= predictor.pit_cutoff (B1) before calling.
    
    Determinism: status depends only on:
      (a) presence of action="retire" in audits, OR
      (b) action="refine" presence (treated as retire for the parent), OR
      (c) recent_window misled count >= retire threshold, OR
      (d) recent_window misled/missed count >= watch threshold
    
    Round 6 fresh-start: legacy mechanism=null branch removed. All v3 lessons
    have non-null mechanism by validator construction. No legacy code path.
    
    No side effects. No file I/O.
    """
    audits = lesson.get("audit_history", [])

    # Explicit retire/refine actions are terminal once visible in PIT
    if any(a.get("action") in ("retire", "refine") for a in audits):
        return "retired"

    recent = audits[-_STATUS_WINDOW:]
    counts = Counter(a.get("review") for a in recent)

    # Threshold retirement (sliding window — naturally absorbing in production
    # because retired lessons aren't rendered, so no new audits accumulate)
    if counts["misled"] >= _RETIRE_MISLED_THRESHOLD:
        return "retired"

    # Watch triggers
    if counts["misled"] >= _WATCH_MISLED_THRESHOLD or \
       counts["missed"] >= _WATCH_MISSED_THRESHOLD:
        return "watch"

    return "active"
```

**Why retirement is naturally absorbing in production** (resolves the v1 review's concern): retired lessons are filtered out by `build_learning_context` → never rendered → predictor never labels them → learner never audits them → no path for new audits to accumulate that could flip status back to active.

**Why retirement is PIT-correct in replay**: since audit_history is PIT-filtered AT RENDER TIME (B1), at any past pit_cutoff `T`, compute_status sees only audits with `audit_pit_cutoff <= T`. If the misled audits that triggered retirement happened AFTER `T`, they're filtered out → status reflects the correct historical state at `T`. If they happened BEFORE `T`, they're visible → status correctly reflects retirement.

### 7.4 Renderer (`renderer/lessons.py`)

**D20 — load-bearing**: the renderer's returned `ordered_lesson_texts` list contains LESSON BODY ONLY. Decoration (status badge, reviews summary, mechanism, applies_when, invalid_if) renders as separate lines AROUND the body but is NOT part of the body string fed to validator T1.

**Render shape**:

```
L2. [sector: <SectorName>] [status: active] [reviews: <Nh> helped, <No> outweighed, <Nm> misled]
Lesson: <single-line body — this becomes lesson_text>
Mechanism: <the causal chain explaining why this lesson worked in THIS event>
Applies when: <bundle preconditions>
Invalid if: <conditions that nullify>
```

The single line after `Lesson:` is what becomes `lesson_text`. Whitespace-collapsed comparison via `_normalize_lesson_text` ensures small formatting differences don't break T1.

**Watch state** (recently misled OR within watch threshold): renders with caution prefix:
```
L4. [ticker: <TICKER>] [status: watch] [reviews: <Nh> helped, <Nm> misled, <No> outweighed]
[CAUTION — recently misled; require sharper bundle confirmation before citing]
Lesson: <body>
Mechanism: <causal chain>
Applies when: <preconditions>
Invalid if: <nullifying conditions>
```

**Retired**: NEVER rendered (filtered upstream in `build_learning_context`).

(Round 6 fresh-start: legacy mechanism=null rendering case removed. All v3 lessons have non-null mechanism by validator construction.)

**iter_labeled_lessons changes**:
- Walk per-quarter ticker rows, then per-lesson within (existing structure)
- For each lesson dict: skip if computed `status == "retired"` (caller of build_learning_context attaches `_render_status` transient field)
- Yield `(n, scope, source_entry, body)` — signature unchanged
- For v3 lesson dicts, body = `lesson_dict["lesson"]`
- v3-only: predictor_lessons entries are dicts; non-dict entries are skipped (round 6 fresh-start removed v1 str-fallback)

```python
def iter_labeled_lessons(learning_ctx: dict):
    n = 0
    for tl in learning_ctx.get("ticker_lessons") or []:
        for pl in tl.get("predictor_lessons") or []:
            if not isinstance(pl, dict):
                continue  # round 6: v3 enforces dict via validator; no str-fallback
            if pl.get("_render_status") == "retired":  # transient field
                continue
            body = pl.get("lesson", "")
            if isinstance(body, str) and body.strip():
                n += 1
                yield (n, "ticker", tl, body)
    by_scope = {"sector": [], "macro": [], "cross_ticker": []}
    for entry in learning_ctx.get("global_lessons") or []:
        if entry.get("_render_status") == "retired":
            continue
        by_scope.setdefault(entry.get("scope"), []).append(entry)
    for scope in ("sector", "macro", "cross_ticker"):
        for entry in by_scope.get(scope, []):
            body = entry.get("lesson", "")
            if isinstance(body, str) and body.strip():
                n += 1
                yield (n, scope, entry, body)
```

### 7.5 PIT and self-leak guards (B1 + D13)

#### 7.5.1 Lesson-level same-quarter self-leak guard (D13)

In `build_learning_context`:

```python
# After existing dedup of ticker_lessons:
if current_quarter_label:
    deduped = [l for l in deduped if l.get("quarter_label") != current_quarter_label]
```

For global lessons (after PIT lesson filter, before scope routing):
```python
if current_quarter_label and ticker:
    if e.get("source_ticker") == ticker and \
       e.get("quarter_label") == current_quarter_label:
        excluded["same_quarter_self_leak"] += 1   # new observability counter
        continue
```

Add `same_quarter_self_leak` to the existing observability log (line ~1811-1819).

#### 7.5.2 Per-lesson audit_history PIT filter (B1 — load-bearing)

In `build_learning_context`, add helper:

```python
def _passes_audit_pit(audit_entry: dict, pit_cutoff: str | None) -> bool:
    """Mirror of _passes_pit but for audit entries (audit_pit_cutoff field).
    Live mode (pit_cutoff is None) → always True.
    Historical mode → audit_pit_cutoff <= pit_cutoff (tz-aware)."""
    if pit_cutoff is None:
        return True
    apc_raw = audit_entry.get("audit_pit_cutoff")
    if apc_raw is None:
        return False  # missing audit_pit_cutoff — defensive exclude in historical mode
    try:
        apc_dt = datetime.fromisoformat(str(apc_raw).replace("Z", "+00:00"))
        cut_dt = datetime.fromisoformat(str(pit_cutoff).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return False
    if apc_dt.tzinfo is None or cut_dt.tzinfo is None:
        return False
    return apc_dt <= cut_dt
```

**Round 9 ordering pin** — `build_learning_context` flow MUST be:

1. Load ticker.json + global.json
2. Lesson-level PIT filter (`_passes_pit` — existing)
3. Same-quarter self-leak guard (§7.5.1)
4. Scope routing + per-scope caps + dedup (existing)
5. **`_apply_render_view` per surviving lesson** — PIT-filter audit_history, compute status, drop `retired` lessons (§7.5.2)
6. **THEN `_decorate_with_learner_paths`** — operates on the filtered+status-decorated list, so retired lessons cannot leak into `_allowed_learner_paths`

If decorate runs before filter, retired lessons' learner_result_paths leak into the bundle's allowlist (functionally OK since predictor never sees retired body, but messy). Filter-first prevents this.

After lesson-level filtering succeeds for a lesson, decorate it with PIT-filtered audit_history + computed render-time status + audit counts:

```python
def _apply_render_view(lesson: dict, pit_cutoff: str | None) -> dict | None:
    """Build a transient view of the lesson with PIT-filtered audit_history,
    computed status, and audit counts. Returns None if status == 'retired'
    so caller can drop the lesson from the bundle."""
    pit_audits = [a for a in lesson.get("audit_history", []) if _passes_audit_pit(a, pit_cutoff)]
    view = {**lesson, "audit_history": pit_audits}
    status = compute_status(view)
    if status == "retired":
        return None
    counts = Counter(a.get("review") for a in pit_audits)
    view["_render_status"] = status
    view["_render_audit_counts"] = dict(counts)
    return view

# Applied to each surviving ticker_lesson and each global_lesson before
# they enter the result dict.
```

**Round-4 clarification — transient `_render_*` field policy** (updated round 7 to flat shape):
- **Library files** (`learnings/ticker/*.json`, `learnings/global.json`): **NEVER** carry `_render_status` or `_render_audit_counts`. These files contain only the canonical fact log + identity + content per §5.2 — for ticker-scope: `lesson_id`, `lesson`, `mechanism`, `applies_when`, `invalid_if`, `evidence_refs`, `scope`, `routing_key`, `audit_history`, `parent_id` (provenance inherits from outer quarter row); for global-scope: same identity+content+state PLUS flat provenance fields (`source_ticker`, `source_sector`, `quarter_label`, `attributed_at`, `source_filed_8k`, `source_pit_cutoff`).
- **Bundle snapshot** (`context_bundle.json`): **MAY** carry `_render_*` keys. The bundle is a frozen snapshot of what the predictor saw at predict-time; preserving the rendered status/counts there aids debugging and ensures the aggregator's later iter_labeled_lessons walk sees the same retired-skip behavior the renderer applied.
- **Aggregator**: when reading the bundle, IGNORE `_render_*` keys (they are not part of canonical state). When updating library files, write only canonical fields.
- **Test invariant**: a test should grep `learnings/**/*.json` for the substring `_render_` and expect zero hits.

### 7.6 Orchestrator-level cross-file validation (D19)

After `validate_attribution_result` passes (success path) OR before recovery-path appends:

```python
def _validate_audit_against_prediction(
    learning_payload: dict,
    prediction_payload: dict,
    bundle: dict,
) -> list[str]:
    """Cross-file validation: lesson_audit must align with prediction.lesson_labels."""
    errors = []
    audits = learning_payload.get("lesson_audit", [])
    labels = prediction_payload.get("lesson_labels", [])

    if len(audits) != len(labels):
        errors.append(f"lesson_audit count {len(audits)} != lesson_labels count {len(labels)}")
        return errors

    indexed = list(iter_labeled_lessons(bundle.get("learning_context", {})))

    # Round-4 correction: D19 self-containment — verify bundle's lesson count
    # matches prediction's label count. T1 (validate_prediction_result line
    # 723-726) already enforces this, but duplicating here makes D19 a
    # complete cross-file gate that doesn't depend on T1 ordering.
    if len(indexed) != len(labels):
        errors.append(
            f"bundle.learning_context lesson count {len(indexed)} != "
            f"lesson_labels count {len(labels)}"
        )
        return errors

    cited = set()
    for kd in prediction_payload.get("key_drivers", []):
        cited.update(kd.get("cites_lesson_indices") or [])

    for i, audit in enumerate(audits):
        if audit.get("lesson_index") != i:
            errors.append(f"lesson_audit[{i}].lesson_index = {audit.get('lesson_index')} (expected {i})")
        if audit.get("predictor_label") != labels[i]["label"]:
            errors.append(f"lesson_audit[{i}].predictor_label mismatch")
        expected_cited = (i in cited)
        if audit.get("was_cited") != expected_cited:
            errors.append(f"lesson_audit[{i}].was_cited = {audit.get('was_cited')} (expected {expected_cited})")
        if i < len(indexed):
            _, _, _, body = indexed[i]
            if _normalize_lesson_text(audit.get("lesson_text", "")) != _normalize_lesson_text(body):
                errors.append(f"lesson_audit[{i}].lesson_text drift from bundle body")

    return errors
```

Failure triggers the existing H2 informed-retry loop (orchestrator:1226-1259), feeding the cross-file errors into the prompt. After 1 retry, if still failing → `FAILED_VALIDATION`.

---

## 8. Validator changes (`scripts/earnings/validate_learning.py`)

### 8.1 v3-only validator (round 6 fresh-start)

Single validator path: only `attribution_result.v3` is accepted. Anything else (including legacy v2 from before cutover) is rejected with a clear error message:

```python
def validate_attribution_result(payload, expected_ticker, expected_quarter):
    sv = payload.get("schema_version")
    if sv != "attribution_result.v3":
        return [
            f"unsupported schema_version: {sv!r} — only attribution_result.v3 is accepted "
            f"(round 6 fresh-start cutover removed v2 read-compat)"
        ]
    return _validate_v3(payload, expected_ticker, expected_quarter)
```

### 8.2 Validator refactor structure (round 9 spec)

Existing `validate_attribution_result` (orchestrator-imported from `validate_learning.py`, ~372 lines) becomes a thin **wrapper** that does schema-version dispatch. **Round 6 is v3-only fresh-start** — the wrapper accepts ONLY `attribution_result.v3` and rejects anything else. Common pre-existing validation rules (top-level required fields, ticker/quarter match, evidence_ledger structure, primary_driver, contributing_factors, feedback caps + comparison shape, global_observations scope routing + scope_key rejection + null-injection rejection, missing_inputs, data_sources_used, ref-field equality) are factored into a private `_validate_common_core(payload, expected_ticker, expected_quarter)` that contains everything EXCEPT the schema_version equality check (owned by the wrapper).

```python
# In validate_learning.py — round 9 refactor:

def validate_attribution_result(payload, expected_ticker, expected_quarter):
    """Wrapper. Dispatches by schema_version; v3-only after round 6."""
    sv = payload.get("schema_version")
    if sv != "attribution_result.v3":
        return [
            f"unsupported schema_version: {sv!r} — only attribution_result.v3 is accepted "
            f"(round 6 fresh-start cutover removed v2 read-compat)"
        ]
    return _validate_v3(payload, expected_ticker, expected_quarter)


def _validate_common_core(payload, expected_ticker, expected_quarter):
    """All non-schema-version-specific rules: top-level required fields,
    ticker/quarter match, evidence_ledger, primary_driver, contributing_factors,
    feedback prediction_comparison + caps, global_observations scope routing
    rules + scope_key rejection + null-injection rejection, missing_inputs,
    data_sources_used, ref fields. Mirrors current validate_attribution_result
    body MINUS the `payload["schema_version"] != "attribution_result.v2"` line.
    """
    errors = []
    # ... existing body, schema_version check REMOVED ...
    return errors


def _validate_v3(payload, expected_ticker, expected_quarter):
    """v3-specific rules: structured predictor_lessons / global_observations
    (mechanism + applies_when + invalid_if + evidence_refs); lesson_audit shape;
    refined_lesson on action=refine; evidence_refs ID resolution."""
    errors = _validate_common_core(payload, expected_ticker, expected_quarter)
    # ... v3 additions per §8.3 ...
    return errors
```

**Hook-validator semantics for `lesson_audit`**: the hook (`.claude/hooks/validate_learning_output.py`) is path-blind — it cannot read prediction/result.json. So it cannot enforce `len(lesson_audit) == len(prediction.lesson_labels)`. The hook validator treats `lesson_audit` as **structurally optional** (if present, must have valid shape; if absent, pass through). The orchestrator's D19 cross-file check is the AUTHORITATIVE coverage gate — it has access to both files and enforces full coverage. This split is intentional: hook fails-closed on schema violations; orchestrator fails-closed on content/coverage violations.

### 8.3 v3 validator (production write path — only path)

Inherits all v2 rules, PLUS:

```python
def _validate_v3(payload, expected_ticker, expected_quarter):
    errors = _validate_common_core(payload, expected_ticker, expected_quarter)

    # Build ledger_ids from THIS payload's evidence_ledger (existing pattern at v2:138-149)
    ledger_ids = {e.get("id") for e in payload.get("evidence_ledger", []) if isinstance(e, dict)}

    # ── Structured predictor_lessons (D17 + N3) ──
    fb = payload.get("feedback", {})
    pl = fb.get("predictor_lessons") or []
    for i, lesson in enumerate(pl):
        if not isinstance(lesson, dict):
            errors.append(f"feedback.predictor_lessons[{i}] must be a dict in v3")
            continue
        for field in ("lesson", "mechanism", "applies_when", "invalid_if"):
            v = lesson.get(field)
            if not isinstance(v, str) or len(v.strip()) < 30:
                errors.append(f"feedback.predictor_lessons[{i}].{field} must be non-empty ≥30 chars")
        # N3 evidence_refs requirement
        refs = lesson.get("evidence_refs")
        if not isinstance(refs, list) or not refs:
            errors.append(f"feedback.predictor_lessons[{i}].evidence_refs must be non-empty list")
        else:
            for ref in refs:
                if ref not in ledger_ids:
                    errors.append(f"feedback.predictor_lessons[{i}].evidence_refs: '{ref}' not in evidence_ledger")

    # ── Structured global_observations ──
    for i, obs in enumerate(payload.get("global_observations") or []):
        for field in ("mechanism", "applies_when", "invalid_if"):
            v = obs.get(field)
            if not isinstance(v, str) or len(v.strip()) < 30:
                errors.append(f"global_observations[{i}].{field} must be non-empty ≥30 chars")
        refs = obs.get("evidence_refs")
        if not isinstance(refs, list) or not refs:
            errors.append(f"global_observations[{i}].evidence_refs must be non-empty list")
        else:
            for ref in refs:
                if ref not in ledger_ids:
                    errors.append(f"global_observations[{i}].evidence_refs: '{ref}' not in evidence_ledger")

    # ── lesson_audit (D8 full coverage) ──
    audits = payload.get("lesson_audit", [])
    if not isinstance(audits, list):
        errors.append("lesson_audit must be a list")
    else:
        for i, audit in enumerate(audits):
            if not isinstance(audit, dict):
                errors.append(f"lesson_audit[{i}] must be a dict")
                continue
            for field in ("lesson_index", "lesson_text", "predictor_label",
                          "was_cited", "review", "action", "comment", "evidence_refs"):
                if field not in audit:
                    errors.append(f"lesson_audit[{i}] missing required field: {field}")
            if not isinstance(audit.get("lesson_index"), int):
                errors.append(f"lesson_audit[{i}].lesson_index must be int")
            if audit.get("review") not in {"helped", "misled", "outweighed", "missed", "neutral", "unclear"}:
                errors.append(f"lesson_audit[{i}].review invalid")
            if audit.get("action") not in {"keep", "refine", "retire"}:
                errors.append(f"lesson_audit[{i}].action invalid")
            if audit.get("predictor_label") not in {"confirmed", "contradicted", "irrelevant"}:
                errors.append(f"lesson_audit[{i}].predictor_label invalid")
            if not isinstance(audit.get("was_cited"), bool):
                errors.append(f"lesson_audit[{i}].was_cited must be bool")
            # B3 fix: evidence_refs IDs must resolve in evidence_ledger
            refs = audit.get("evidence_refs")
            if not isinstance(refs, list):
                errors.append(f"lesson_audit[{i}].evidence_refs must be a list")
            else:
                for ref in refs:
                    if ref not in ledger_ids:
                        errors.append(f"lesson_audit[{i}].evidence_refs: '{ref}' not in evidence_ledger")
            # action=refine requires replacement_lesson with full structure + evidence_refs
            if audit.get("action") == "refine":
                rl = audit.get("replacement_lesson")
                if not isinstance(rl, dict):
                    errors.append(f"lesson_audit[{i}]: action='refine' requires replacement_lesson dict")
                else:
                    for field in ("lesson", "mechanism", "applies_when", "invalid_if"):
                        v = rl.get(field)
                        if not isinstance(v, str) or len(v.strip()) < 30:
                            errors.append(f"lesson_audit[{i}].replacement_lesson.{field} must be non-empty ≥30 chars")
                    rrefs = rl.get("evidence_refs")
                    if not isinstance(rrefs, list) or not rrefs:
                        errors.append(f"lesson_audit[{i}].replacement_lesson.evidence_refs must be non-empty list")
                    else:
                        for ref in rrefs:
                            if ref not in ledger_ids:
                                errors.append(f"lesson_audit[{i}].replacement_lesson.evidence_refs: '{ref}' not in evidence_ledger")

    return errors
```

### 8.4 What the validator does NOT enforce

- **NOT** "threshold-without-mechanism" semantic checks (D5 — regex-prone, false-positive-heavy)
- **NOT** mechanism content quality (subjective)
- **NOT** lesson_audit count vs prediction.lesson_labels count — see D19 / §7.6 (orchestrator-level)
- **NOT** lesson_text matching bundle body — see D19 / §7.6 (orchestrator-level)

The validator is hook-safe (stdlib-only, no prediction-file access). The cross-file checks (D19) live in the orchestrator where both files are accessible.

---

## 9. SKILL.md changes

### 9.1 `.claude/skills/earnings-learner/SKILL.md` (~50 lines net)

**Phase 1 — Load Context** — add step 4.5:

> **4.5 Read predictor's lesson labels and citations.** Open `PREDICTION_RESULT` and read `prediction["lesson_labels"]` (predictor's `confirmed`/`contradicted`/`irrelevant` calls on prior lessons) and `prediction["key_drivers"][i]["cites_lesson_indices"]` (which confirmed lessons the predictor leaned on). These are bundle-evidence judgments the predictor made BEFORE knowing the outcome. With hindsight, you will now audit each one against actual_return.

**Phase 2 — Investigate** — add three-scope probes (in addition to existing investigation guidance):

> When attributing the move, explicitly ask at each of the three scopes:
> 1. **Company-specific**: What about THIS company specifically explains the reaction? Identify the specific feature; do not pattern-match from a checklist.
> 2. **Sector-wide**: Did peers react similarly to similar inputs this quarter? If yes, what shared condition is the market focused on right now?
> 3. **Macro regime**: Did broad-market regime conditions directly explain the reaction?
>
> Each scope can produce 0 or 1 lessons. **Most quarters won't yield lessons at all three scopes.** The bar is: "is the mechanism specific enough to not be a tautology?"

**Phase 4 — Distill Lessons** — replace the existing `predictor_lessons` and `global_observations` instructions with structured-output rules:

> Every lesson you emit (in `predictor_lessons` or `global_observations`) must be a structured object with five required fields:
>
> - `lesson` (≥30 chars) — the heuristic itself, 1-2 sentences
> - `mechanism` (≥30 chars) — the causal chain. Why does this work?
> - `applies_when` (≥30 chars) — the bundle preconditions for the lesson to fire
> - `invalid_if` (≥30 chars) — the negative case. What conditions nullify or invert this lesson?
> - `evidence_refs` (≥1 entry) — list of evidence_ledger IDs from THIS quarter that DIRECTLY DEMONSTRATE the mechanism (not tangential evidence). Validator cross-checks IDs exist.
>
> **Scope-choice protocol — choose the NARROWEST justified scope** (default conservative; expand only when evidence forces it). Decision rules only — do NOT use these as mechanism templates:
> - **`predictor_lessons` (ticker scope)** — mechanism is rooted in THIS company; the lesson would NOT transfer to peers unchanged.
> - **`global_observations` with `scope: "sector"`** — peers in the same sector would plausibly react similarly to similar inputs.
> - **`global_observations` with `scope: "macro"`** — broad-market regime directly explains the reaction.
> - **`global_observations` with `scope: "cross_ticker"`** — explicit named-company transmission link (shared customer, shared supply, shared regulatory framework). NOT a sector-wide lesson; specific to the named set.
>
> **Default to narrower if you can defend it.** Over-broadening routes the lesson to MANY future predictions and can MISLEAD peer-ticker calls. Under-routing only hurts coverage. The asymmetry favors narrower-when-uncertain.
>
> **Every mechanism must name what the market REWEIGHTED THIS QUARTER and why.** Which fundamental did investors shift focus to this quarter, and what caused that shift? Without naming the reweighting AND the causal WHY, you have a slogan, not a lesson.
>
> **Valid-lesson rubric.** A lesson is valid if and only if it:
> 1. Identifies the SPECIFIC driver the market reweighted THIS quarter (not a generic factor)
> 2. Explains the causal transmission mechanism (who reprices what, and why)
> 3. States the conditions under which it applies (`applies_when`)
> 4. States the conditions that nullify it (`invalid_if`)
> 5. Cites `evidence_refs` that DIRECTLY prove the mechanism is present in this quarter's bundle
>
> **Invalid-lesson signals — emit NO lesson if any apply:**
> - Only describes price patterns or peer movement without explaining transmission
> - Uses generic phrases ("sell the news", "buy the dip", "stocks like this go down")
> - Applies equally to any company / sector / regime (tautology)
> - Embeds thresholds disconnected from mechanism (specific numbers without causal WHY)
> - Memorizes prior outcomes (recall without mechanism)
> - Has a `mechanism` longer than the `lesson` body (fluff inflation)
> - Uses vague actors ("investors", "the market", "analysts") without naming WHICH segment
> - Cites `evidence_refs` that don't directly prove the mechanism (tangential)
>
> **When in doubt, emit fewer lessons.** Empty `predictor_lessons: []` is acceptable. Padded lessons are not.

**Phase 4 — Distill Lessons** — add audit decision tree:

> **Audit each labeled lesson in the prediction**. Emit exactly one `lesson_audit[i]` entry per `prediction.lesson_labels[i]`. The `lesson_index` is positional (0-based, matching the prediction array). Choose `review` from this decision tree:
>
> - Predictor `confirmed` + cited + outcome aligned → `review: helped, action: keep`
> - Predictor `confirmed` + cited + outcome wrong, mechanism present + correct (other forces dominated) → `review: outweighed, action: keep` (or `refine` if applies_when needs tightening)
> - Predictor `confirmed` + cited + outcome wrong, mechanism NOT actually present → `review: misled, action: refine` (sharpen trigger) or `retire` (no salvage)
> - Predictor `irrelevant` + correctly so → `review: neutral, action: keep`
> - Predictor `irrelevant` + lesson actually applicable → `review: missed, action: refine`
> - Predictor `contradicted` correctly → `review: neutral, action: keep`
> - Predictor `contradicted` + lesson actually right → `review: missed, action: refine`
> - Hindsight cannot decide → `review: unclear, action: keep`
>
> Every audit's `comment` must be one sentence citing actual_return AND/OR specific `evidence_ledger` IDs. Every audit's `evidence_refs` must list ledger IDs that justify the verdict.
>
> **Refinement protocol.** If `action: "refine"`, you MUST include `replacement_lesson` with all five fields (lesson + mechanism + applies_when + invalid_if + evidence_refs). Replacement should fix the specific failure mode you observed. Do NOT use refine for cosmetic edits.

**Critical Rules** — add #9, #10, and #11:

> **9. Mechanism, not pattern.** Every lesson must explain WHY the heuristic works AND cite at least one evidence_ledger ID from THIS quarter that DIRECTLY demonstrates the mechanism. Memorized correlations without mechanism are coincidences, not lessons.
>
> **10. Audit honestly.** Distinguish `misled` (lesson was bad) from `outweighed` (lesson was sound but other forces won) from `missed` (predictor failed to use a good lesson). Hindsight is asymmetric — be specific about cause, not just outcome.
>
> **11. Ground every lesson in THIS quarter's specific reaction.** A lesson should answer: what did THIS QUARTER's reaction reveal about how the company/sector/macro is being graded? It should NOT be a recall of prior quarters or a generic financial maxim. The `evidence_refs` you cite must be entries from THIS learner run's `evidence_ledger` that DIRECTLY demonstrate the mechanism — not tangential supporting detail. **Fewer high-quality lessons beat more low-quality lessons**: emit `predictor_lessons: []` rather than fill the cap with weak entries.

### 9.2 `.claude/skills/earnings-prediction/SKILL.md` (~12 lines net)

Add to §3.3 Lesson Labeling, after the existing label-choice paragraph:

> **Mechanism gate.** A lesson's `mechanism` must independently apply to THIS quarter's bundle for `label = "confirmed"`. Generic, abstract, or thematically plausible mechanisms not bundle-confirmable from current evidence → label `irrelevant`.
>
> **Track record signal.** Each lesson shows `[reviews: Nh helped, Nm misled, ...]`. A `[status: watch]` lesson requires sharper bundle evidence than `active`. A streak of `misled` audits is a prior against citation; require especially strong mechanism alignment in this bundle to overcome it. Reviews are guidance, not verdict.
>
> **lesson_text discipline (D20).** When copying a lesson into `lesson_labels[i].lesson_text`, copy ONLY the `Lesson:` body line — NOT the status badge, reviews summary, mechanism, applies_when, or invalid_if. The validator's positional equality check compares against the body only. Including decoration breaks T1.

---

## 10. Fresh-start cutover (round 6 — replaced migration)

### 10.1 Existing data — wiped before v3 cutover

The existing v1/v2 lesson library and v2 attribution result files are too thin to be worth migrating (2 ticker quarters, 6 global entries, 2 attribution result files — all from a small AVGO seed corpus). Round 6 decision: **wipe and start fresh.** Removes all legacy complexity (no v2 read-compat, no migration script, no mechanism=null branch, no legacy renderer fallback, no v2 dispatch in aggregator/validator).

| File | Action |
|------|--------|
| `learnings/ticker/AVGO.json` | **DELETE** before cutover |
| `learnings/global.json` | **DELETE** before cutover |
| `Companies/{TICKER}/events/{Q}/learning/result.json` (any v2 file) | **DELETE** before cutover |
| `Companies/{TICKER}/events/{Q}/prediction/result.json` (existing v1 predictions) | **KEEP** — predictor schema unchanged; existing predictions retain `lesson_labels: []` because their bundle had no prior lessons (which is correct given the wiped library) |
| `Companies/{TICKER}/events/{Q}/context_bundle.json` (existing bundles) | **REGENERATE** at next prediction run; old bundles' learning_context is stale (referenced wiped library) |

### 10.2 Cutover procedure (replaces migration script)

One-shot bash command, run AFTER all 4 commits land + before §13.5 production gates:

```bash
# Backup (defensive — kept for ~1 quarter then deletable)
cd /home/faisal/EventMarketDB
mkdir -p earnings-analysis/.pre-v3-cutover-backup
cp -a earnings-analysis/learnings/ \
      earnings-analysis/.pre-v3-cutover-backup/ 2>/dev/null || true
find earnings-analysis/Companies -path "*/events/*/learning/result.json" \
     -exec cp --parents {} earnings-analysis/.pre-v3-cutover-backup/ \;

# Wipe library
rm -f earnings-analysis/learnings/ticker/*.json
rm -f earnings-analysis/learnings/global.json
rm -f earnings-analysis/learnings/global.lock

# Wipe v2 attribution result files (force regeneration as v3)
find earnings-analysis/Companies -path "*/events/*/learning/result.json" -delete
find earnings-analysis/Companies -path "*/events/*/learning/result.md" -delete

# Initialize empty v3 library files (validator-compatible)
mkdir -p earnings-analysis/learnings/ticker
echo '{"schema_version":"global_lessons.v2","updated_at":null,"entries":[]}' \
  > earnings-analysis/learnings/global.json
```

Per-ticker `learnings/ticker/{TICKER}.json` files are created on demand by `append_ticker_lesson` at first write (existing behavior; orchestrator:1330-1335).

**No migration script. No `.v1.bak` files mixed in with library. No legacy data in production tree.**

Run order: ensure tests pass on a copy first → backup → wipe → init empty global → green-light v3 writes.

**Naming clarification (round 6)**: there are TWO independent schema-version namespaces in this design — do not confuse them:
- `attribution_result.v3` — the LEARNER OUTPUT schema (what the learner writes to `events/{Q}/learning/result.json`); validator only accepts v3.
- `ticker_lessons.v2` / `global_lessons.v2` — the STORAGE schemas (what the orchestrator writes to `learnings/ticker/{TICKER}.json` and `learnings/global.json`); these "v2" tags indicate the structured-lesson-dict shape and are unrelated to attribution_result versioning. Storage v1 was the pre-cutover string-only shape; storage v2 is the round-6 fresh-start shape.

### 10.3 No backward read-compat

Round 6 fresh-start: validator + iter_labeled_lessons + renderer assume v3 lesson_dicts only. No defensive str-branch, no `(not recorded)` legacy fallback, no v2 schema dispatch. Cleaner code surface. If any v2 file unexpectedly appears (shouldn't — wipe step removes them), validator rejects loudly.

---

## 11. Edge cases — full catalog

| # | Case | Handling |
|---|------|----------|
| E1 | Empty `lesson_audit[]` (first prediction with no priors) | Aggregator early-return; orchestrator cross-file check passes (0 == 0) |
| E2 | `lesson_index` out of range | Aggregator log warning, skip (D19 cross-file would have rejected; defensive only) |
| E3 | `lesson_text` mismatches body at `lesson_index` | D19 cross-file rejects; aggregator defensive |
| E4 | Bundle has lessons but predictor wrote `lesson_labels: []` | T1 validator already rejects |
| E5 | Learner re-run for same quarter (recovery) | Aggregator runs in recovery path (D18); upsert by `(auditor_ticker, auditor_quarter_label)` — replaces, no dup |
| E6 | Two parallel learners (different tickers) audit SAME global lesson | global.json flock protects writes; distinct upsert keys |
| E7 | Lesson body changes between render and audit (impossible — same bundle) | Aggregator reads bundle on disk; iter_labeled_lessons walks identical to render |
| ~~E8~~ | ~~Mechanism field absent on legacy library entry~~ | **REMOVED** (round 6 fresh-start): v3 validator enforces non-null mechanism; no legacy entries exist post-cutover |
| E9 | `replacement_lesson` has same hash as parent | Aggregator: if computed lesson_id of replacement == parent_id, treat as `action: keep` (log warning) |
| E10 | Lesson_id collision across scopes | Hash includes scope+routing → impossible by construction |
| E11 | Status flap (watch → active → watch) under sliding window | Acceptable in production: retired is naturally absorbing because retired lessons aren't rendered → no new audits accumulate. Watch ↔ active flap is correct (lesson genuinely fluctuating in a regime change) |
| E12 | Library file missing / corrupted | Existing JSON-decode error handling (orchestrator:1703-1706, 1792-1795) |
| E13 | Learner forgets `mechanism`/`evidence_refs` on a new lesson | v3 validator rejects → existing H2 informed-retry kicks in |
| E14 | Audit-history grows large | No cap (N1). Storage trivial (~100 bytes/entry); status uses last 5 only |
| E15 | Cross-ticker lesson cited by ticker NOT in `related_tickers` | Existing routing prevents render; no audit can come from there |
| E16 | Same-quarter self-leak in live re-run | NEW guard in `build_learning_context` filters `(source_ticker, quarter_label) == (ticker, current_quarter_label)` for both ticker_lessons and global_lessons |
| ~~E17~~ | ~~Migration interrupted mid-file~~ | **REMOVED** (round 6): no migration script; cutover is single bash wipe in §10.2 |
| E18 | Refined lesson MUST have same scope+routing as parent (round 7 design) | Inherited by `_register_replacement` — refinement does NOT change scope/routing. To change scope, learner must retire the parent (action=retire) AND emit a separate new lesson at the new scope normally. Cross-ticker contamination on ticker-scope refinement is impossible by construction (auditor_ticker is authoritative for the routing_key) |
| E19 | Cycle in parent_id chain | Impossible by construction — retired lessons can't be refined; new lessons get fresh `lesson_id` |
| E20 | Live mode learner runs before next live prediction (different event) | Same-quarter guard fires only on (same ticker, same quarter); cross-quarter is normal flow |
| E21 | Predictor missing `cites_lesson_indices` on a key_driver | Existing T1 validator rejects (line 736-738); never reaches aggregator |
| E22 | All 5 recent audits are `outweighed` | Status stays `active` (D6) — lesson sound, others won; correct |
| E23 | Refinement of an already-retired lesson | Cannot happen in production (retired not rendered); manual override out of scope |
| E24 | Audit's `evidence_refs` reference IDs not in evidence_ledger | v3 validator rejects (B3) |
| E25 | Same lesson_id in BOTH ticker.json AND global.json | Cannot happen — scope+routing differ; different IDs |
| E26 | Aggregator partial failure (writes ticker.json, crashes before global.json) | Re-run learner orchestration is idempotent; upsert keys converge to consistent state |
| E27 | Audit lesson_text ≠ bundle body at lesson_index | D19 orchestrator-level check rejects; H2 retry prompts learner |
| **E31** (round 9) | Refinement on global lesson is a multi-write (audit-append on parent + new-entry insert) | Both writes happen under a SINGLE flock acquisition on `global.lock`. Acquire flock → load → append audit to parent's audit_history → append new entry → write atomically → release. Readers between the two writes would see audit-without-replacement; single-flock prevents this race. |
| **E32** (round 9) | D19 cross-file errors need to drive H2 retry | Merge into existing `prior_validation_errors: list[str]` with prefix `"[cross-file] "` so the retry prompt distinguishes them from schema errors. Same retry path; same FAILED_VALIDATION outcome on still-failing retry. |
| **E33** (round 9) | result_md_renderer doesn't render lesson_audit cleanly | **Accepted as deferred**: existing `_learning_body()` json-dumps unknown dicts; v3's new `lesson_audit[]` will render as raw JSON in result.md. Functionally correct, visually ugly. Defer proper rendering to a follow-up commit; not blocking for production gates. **Round 10 backlog note**: if production gates pass and result.md readability becomes a launch concern (e.g., for Obsidian-side review of recent learning runs), add a small `_render_lesson_audit_table` helper to `result_md_renderer.py::_learning_body()` rendering the audit as a Markdown table (auditor_quarter / review / action / comment / evidence_refs columns). Estimated diff: ~30 lines + 1 test. |
| **E34** (round 9) | Pre-step backup files (`result.json.pre-stepN-backup`) survive cutover wipe | Cutover bash uses exact-name `find ... -name "result.json"`. Stale backups in `prediction/` directories aren't part of the v3 cutover scope — they're predictor-side leftovers. If a `.pre-stepN-backup` ever lands in `learning/`, broaden the wipe glob: `find ... -path "*/learning/result*" -delete`. Preferred: leave exact-name match (defensive — don't accidentally delete unrelated files). |
| E28 | Future audit_history visible during historical replay | B1 fix: `_passes_audit_pit` filters audits by `audit_pit_cutoff <= pit_cutoff` |
| E29 | Future-retired lesson hidden during historical replay | Resolved by B1: at replay PIT < retirement-trigger audits, retirement-triggering audits filtered out → status reverts to active correctly |
| ~~E30~~ | ~~Legacy lesson never accumulates pressure~~ | **REMOVED** (round 6 fresh-start): no legacy lessons exist; library is wiped before v3 cutover |

---

## 12. Tests

| Test file | New / extended | Coverage |
|-----------|----------------|----------|
| `test_validate_learning_v3.py` (new) | All v3 schema rules: structured lessons, evidence_refs ID resolution (B3), lesson_audit shape, review/action enums, replacement_lesson on refine |
| ~~`test_validate_learning.py` (v2 dispatch)~~ | **REMOVED** (round 6): only v3 accepted; replaced by reject-non-v3 test in `test_validate_learning_v3.py` |
| `test_aggregate_lesson_audits.py` (new) | Audit append, idempotency, refinement chain, retire action, lesson_index range checks, lesson_text drift warning, **runs in success path AND recovery path** (D18); **empty-`predictor_lessons` + ticker-scope `action="refine"` → aggregator creates auditor quarter row from `learning_payload` outer fields and inserts replacement** (see §7.2.1 implementation rule) |
| `test_lesson_status_transitions.py` (new) | Pure-function table: every (audit pattern → expected status). Specific cases: 3 misled→retired, 2 misled→watch, 5 outweighed→active, mixed misled+missed, **action="retire" terminal**, **action="refine" terminal (same retire semantics as action="retire")**. (Round 6 fresh-start removed mechanism=null legacy cases — all v3 lessons have non-null mechanism by validator construction.) |
| `test_audit_history_pit_filter.py` (new — B1) | Lesson visible at PIT but with future audits → audits filtered, status correct, retirement-triggering future audits hidden in earlier replays |
| ~~`test_legacy_lesson_lifecycle.py`~~ | **REMOVED** (round 6 fresh-start): no legacy lessons exist post-cutover |
| `test_evidence_refs_resolve.py` (new — B3) | v3 validator rejects audit/lesson with evidence_refs IDs not in evidence_ledger |
| `test_aggregator_recovery_path.py` (new — D18) | Recovery path (orchestrator:1142-1167) calls aggregator after appends; library state matches success-path baseline |
| `test_orchestrator_cross_file_validation.py` (new — D19) | Mismatches in count/lesson_text/predictor_label/was_cited each trigger H2 retry; valid case passes |
| `test_lesson_id_stability.py` (new) | Same body+scope+routing → same id; refinement → different id; cross-scope same-text → different id; collision check on synthetic corpus |
| ~~`test_migrate_learnings_v1_to_v2.py`~~ | **REMOVED** (round 6 fresh-start): no migration script; cutover is one-shot bash wipe per §10.2 |
| `test_render_lessons_v2.py` (extended `test_render_learning_context.py`) | Active/watch/retired display; mechanism block; applies_when block; invalid_if block; reviews summary; CAUTION prefix on watch; **ordered_lesson_texts contains body only (D20)** |
| `test_pit_self_leak_guard.py` (new) | `build_learning_context` excludes (source_ticker, quarter_label) == (ticker, current_quarter_label) for both ticker and global; new `same_quarter_self_leak` counter |
| `test_iter_labeled_lessons_v2.py` (new) | Skips retired lessons (via `_render_status` transient field); v3-dict-only (round 6 removed str-fallback) — non-dict entries skipped; n only increments on non-empty bodies; **structured ticker lessons map to distinct IDs** |
| `test_loop_round_trip_smoke.py` (new — N4) | True audit-loop coverage requires three quarters because fresh-start has no priors at Q3. Sequence: predict Q3 (lesson_labels=[] — no priors) → learn Q3 (writes new lessons, no audits to write) → predict Q4 (sees Q3's lessons in bundle, labels them) → learn Q4 (audits Q3's lessons → aggregator writes audit_history) → predict Q5 (sees Q3's lessons WITH non-empty audit_history; verify review counts rendered correctly). **Alternative**: synthesize seed lessons + seed audits directly into the library to compress to a single quarter; document which approach the test uses. |
| `test_renderer_golden_full.py` (extended) | Goldens regenerated post-cutover; byte-exact compare |
| `test_validate_prediction_result_v3.py` (extended) | T1 positional equality still works against the new structured-dict storage shape (renderer's body output is the lesson string from `lesson_dict["lesson"]`) |

**Estimated test LOC delta**: ~500 lines new + ~50 lines extended.

---

## 13. Implementation sequence

Single PR, 4 stacked commits. Smoke between each.

| # | Commit | Files | Includes |
|---|--------|-------|----------|
| 1 | `feat(learner): v3 schema + structured lessons + lesson_audit validator` | `validate_learning.py`, `test_validate_learning_v3.py`, `test_evidence_refs_resolve.py` | v3-only validation (rejects non-v3); B3 evidence_refs ID resolution; N3 evidence_refs on new lessons |
| 2 | `feat(orchestrator): aggregator + status state machine + PIT audit filter + same-quarter guard + cross-file validation` | `earnings_orchestrator.py`, `_text_utils.py`, `test_aggregate_lesson_audits.py`, `test_lesson_status_transitions.py`, `test_audit_history_pit_filter.py`, `test_pit_self_leak_guard.py`, `test_aggregator_recovery_path.py`, `test_orchestrator_cross_file_validation.py`, `test_iter_labeled_lessons_v2.py`, `test_lesson_id_stability.py` | aggregator (D18 success+recovery); compute_status (D17); _passes_audit_pit (B1); same-quarter guard (D13); orchestrator cross-file check (D19); iter_labeled_lessons skip retired |
| 3 | `feat(renderer): mechanism + applies_when + invalid_if + status badge + reviews summary` | `renderer/lessons.py`, `test_render_lessons_v2.py`, `test_renderer_golden_full.py` | D20 (body-only); CAUTION prefix on watch |
| 4 | `feat(skills): learner v3 prompt + predictor mechanism gate + lesson_text discipline` + fresh-start cutover | `.claude/skills/earnings-learner/SKILL.md`, `.claude/skills/earnings-prediction/SKILL.md`, `test_loop_round_trip_smoke.py`, then run §10.2 cutover bash on actual `learnings/*` + `Companies/*/events/*/learning/*` files | Activation. Round 6: no migration script; single bash wipe + empty-init |

After commit 4 + cutover: AVGO Q4 historical smoke (predict + learn against fresh-start library — first prediction will see empty `## Lessons To Label`; learner will write the first v3 lessons; second AVGO event tests round-trip) → verify result.md and library state. Then cross-sector smoke (CRM Q4 or BURL).

### 13.5 Post-implementation production verification gates

After all 4 commits land, run these gates against real data before declaring the loop production-ready. The unit tests in §12 are gating for code correctness; these gates are gating for end-to-end pipeline behavior.

| # | Gate | What to verify | Min gate | Preferred |
|---|------|----------------|----------|-----------|
| **G1** | **Fresh-start cutover smoke** | Run §10.2 wipe + init on a COPY of the production tree first. Confirm: empty `learnings/global.json` with valid JSON, no `learnings/ticker/*.json` files remaining, no `events/*/learning/result.json` files remaining, `events/*/prediction/result.json` files preserved, `events/*/context_bundle.json` files preserved (will regenerate at next predict). | ✅ | ✅ |
| **G2** | **Historical PIT leak test** | After fresh-start cutover the library is empty, so seed BOTH a synthetic v3 lesson (with `source_pit_cutoff = Q3.filed_8k`) AND a synthetic future audit on it (with `audit_pit_cutoff = Q5.filed_8k`). Replay an AVGO Q4 prediction (pit_cutoff between Q3 and Q5 — e.g., Q4.filed_8k). Confirm: future audit invisible in render, review count unaffected, status reflects only PIT-visible audits. **CRITICAL — do not ship without this.** | ✅ | ✅ |
| **G3** | **Full-loop smoke** | Fresh-start at Q3 has no priors, so a one-quarter loop wouldn't exercise audit_history rendering. Run **3 quarters** OR seed synthetics: predict Q3 (lesson_labels=[]) → learn Q3 (writes new lessons, no audits) → predict Q4 (sees Q3 lessons in bundle, labels them) → learn Q4 (audits Q3 lessons → aggregator writes audit_history) → predict Q5 (sees Q3 lessons WITH non-empty audit_history). Verify Q5 bundle's lesson rendering shows review counts from Q4 audits; any retired lesson dropped; any refined lesson visible with parent_id link. **CRITICAL — do not ship without this.** Alternative: synthesize seed lessons + audits into the library to compress to a single quarter; document the approach in the test. | ✅ | ✅ |
| **G4** | **Retire test** | Force 3 sequential `misled` audits on a synthetic test lesson. Run aggregator after each. After the 3rd, confirm: status=retired, lesson excluded from next bundle's render, audit_history retains all three entries, no rerun-fragility on aggregator re-execution. | ✅ | ✅ |
| **G5** | **Refine test** | Set `action: "refine"` with valid `replacement_lesson` on a test lesson. Confirm: parent's audit_history gains the refine entry, parent compute_status returns "retired" (line 550), replacement lesson registered with parent_id link, replacement renders in next bundle while parent does NOT. | ✅ | ✅ |
| ~~G6~~ | ~~Legacy lesson test~~ | **REMOVED** (round 6 fresh-start): no legacy lessons exist; no test needed |
| **G7** | **Same-quarter self-leak test** | Re-run AVGO Q4 prediction in live mode (pit_cutoff=None) AFTER its learner has populated AVGO Q4 lessons. Confirm: AVGO Q4's own lessons (source_ticker=AVGO + quarter_label=Q4_FY2023) are excluded from the rebuild's bundle. `same_quarter_self_leak` counter > 0 in observability log. | ✅ | ✅ |
| G8 | **Global/sector propagation test** | After AAPL Q3 learner writes a sector="Technology" lesson, run MSFT Q4 prediction (later filing date, same sector). Confirm: lesson visible. Then run a non-Tech ticker prediction (e.g., XOM); confirm lesson NOT visible. Same propagation rules for cross_ticker scope. | — | ✅ |
| G9 | **Validator retry test** | Simulate learner output missing `evidence_refs` on a predictor_lessons entry, OR with lesson_audit count != prediction.lesson_labels count. Confirm: validator (or D19 orchestrator-level check) rejects, H2 informed-retry kicks in, retry's prompt includes the cross-file errors. | — | ✅ |
| **G10** | **Real SDK end-to-end smoke** | Run actual SDK invocation: AVGO Q4 historical predict + learn + aggregate + Q1_FY2024 bundle rebuild. Inspect: `prediction/result.json` (v1 with structured lesson_labels), `learning/result.json` (v3 with lesson_audit + structured lessons + evidence_refs), `learnings/ticker/AVGO.json` (v2 with audit_history populated), next bundle's rendered lessons (mechanism + reviews + status badges). | ✅ | ✅ |

**Minimum acceptable gate**: G1, G2, G3, G4, G5, G7, G10 (= 7 of 9 active gates; G6 removed in round 6).
**Preferred production gate**: all 9 active gates.
**Hard rule**: do not declare production-ready without **G2** (historical PIT leak) AND **G3** (full-loop smoke) passing. Without G2, backtests silently see future audits. Without G3, the closed loop has never been verified end-to-end.

**Failure handling**: any gate failure halts the production rollout. Investigate the failure, patch in a follow-up commit (with isolated test that catches the specific issue), re-run all gates from G1.

---

## 14. Tunable parameters

```python
# scripts/earnings/earnings_orchestrator.py — config block
LESSON_AUDIT_WINDOW = 5             # recent audits considered for status
LESSON_RETIRE_MISLED_THRESHOLD = 3  # misled count → retired
LESSON_WATCH_MISLED_THRESHOLD = 2   # misled count → watch
LESSON_WATCH_MISSED_THRESHOLD = 2   # missed count → watch
# (no audit_history cap — N1)
```

Adjustable post-launch based on observed behavior.

---

## 15. Decision log (load-bearing for future-me)

| Date | Decision | Author | Reason |
|------|----------|--------|--------|
| 2026-05-03 | Pivot from prose-only MVP (§13.18) to structured prior_lesson_audit | ChatGPT | Prose-only too weak for self-healing |
| 2026-05-04 | Use 6-value review enum (helped/misled/outweighed/missed/neutral/unclear) | ChatGPT | `missed` distinguishes lesson-failure from predictor-failure |
| 2026-05-04 | Storage stays quarter-row-shaped on ticker.json | ChatGPT | Preserves Context-Only block + iter_labeled_lessons + decorate_with_learner_paths |
| 2026-05-04 | Bump to attribution_result.v3 (not silent v2 additions) | ChatGPT | Production hygiene |
| 2026-05-04 | Validator enforces field existence + length only (NOT semantic content) | ChatGPT | Regex semantic checks brittle |
| 2026-05-04 | Conservative status thresholds; outweighed never retires | ChatGPT | Penalizing outweighed damages good lessons |
| 2026-05-04 | Add `invalid_if` field alongside `applies_when` | ChatGPT | Forces failure-condition reasoning |
| 2026-05-04 | Audit entries carry both lesson_index + lesson_text + evidence_refs | ChatGPT + Claude | Defense in depth |
| 2026-05-04 | ~~Legacy lessons handled via mechanism=null + compute_status branch~~ — **SUPERSEDED by round 6 fresh-start** (no legacy lessons exist post-cutover; mechanism=null branch removed entirely) | Claude refinement | Original rationale: avoid 4th status enum. Round-6 resolution: wipe legacy entirely; mechanism=null path no longer needed |
| 2026-05-04 | PIT self-leak guard added (orchestrator gap) | ChatGPT caught | Real bug |
| 2026-05-04 | Field name `lesson_audit` (not `prior_lesson_reviews`) | Claude | Pairs with `audit_history` |
| 2026-05-04 | data_lessons stay as `list[str]` | Both agreed | Not market hypotheses |
| 2026-05-04 | Caps stay 3/3/3; lesson_audit uncapped (full coverage) | ChatGPT | Capping audit forces incomplete coverage |
| **2026-05-04 (v2)** | **D17: Status COMPUTED at read time, not stored** | Claude review | Resolves PIT correctness automatically; eliminates dual-source-of-truth |
| **2026-05-04 (v2)** | **D18: Aggregator runs in BOTH success and recovery paths** | ChatGPT review | orchestrator:1162-1167 currently bypasses aggregation in recovery |
| **2026-05-04 (v2)** | **D19: Orchestrator-level cross-file validation REQUIRED** | ChatGPT review | Hook validator can't access prediction file; schema validation alone allows audit drift |
| **2026-05-04 (v2)** | **D20: Renderer ordered_lesson_texts = lesson body only** | ChatGPT review | T1 validator's positional equality compares against body; decoration must NOT bleed in |
| **2026-05-04 (v2)** | **B1 fix: PIT-filter audit_history per lesson** | Claude review | Future-leak in historical replay would corrupt backtests |
| **2026-05-04 (v2)** | ~~B2 fix: Legacy lessons (mechanism=null) start at `watch`~~ — **SUPERSEDED by round 6 fresh-start** (no legacy lessons exist post-cutover; B2 branch removed from compute_status) | Claude review | Original rationale: without this, legacy clogs bundle indefinitely. Round-6 resolution: wipe legacy entirely; no clogging risk |
| **2026-05-04 (v2)** | **B3 fix: validator cross-checks evidence_refs IDs against ledger** | Claude review | Forces grounding discipline |
| **2026-05-04 (v2)** | **N1: drop 20-entry audit_history cap** | Claude review | Storage trivial; cap broke replay observability |
| **2026-05-04 (v2)** | **N3: new lessons require evidence_refs** | Claude review | Same grounding discipline as audits |
| **2026-05-04 (round 4)** | **All v2 corrections (D17–D20, B1, B2, B3, N1, N3) confirmed by ChatGPT round 4 review** | ChatGPT round 4 | Independent verification — same conclusions reached |
| **2026-05-04 (round 4)** | **Add §13.5 production verification gates (10 tests)**; G2 (historical PIT leak) + G3 (full-loop smoke) hard-gated for ship | ChatGPT round 4 | End-to-end verification beyond unit tests; live-data validation of the closed loop |
| **2026-05-04 (round 4 final)** | ~~Legacy mechanism=null check uses FULL PIT-visible audit_history~~ — **SUPERSEDED by round 6** (mechanism=null branch removed entirely; no legacy lessons exist) | ChatGPT round 4 | Original purpose: prevent oscillation as helped audit ages off window. Round-6 made this branch obsolete |
| **2026-05-04 (round 4 final)** | **D19 cross-file validation self-contained** — adds `len(indexed) == len(labels)` check (redundant with T1 but defensive) | ChatGPT round 4 | D19 is the orchestrator-level cross-file gate; should not depend on T1 ordering for its own invariants |
| **2026-05-04 (round 4 final)** | **Transient `_render_*` field policy explicit**: library files NEVER carry; bundle snapshot MAY carry; aggregator ignores | ChatGPT round 4 | Prevents canonical state pollution while preserving snapshot integrity for debugging |
| **2026-05-04 (round 4 final)** | **Wording: "no new runtime services/agents/schedules/DBs"** (replaced "no new files" — plan does add 1 migration script + ~16 test files) | ChatGPT round 4 | Honest accounting of the additions |
| **2026-05-04 (round 4 final)** | **Test for `action="refine"` terminal explicit in test_lesson_status_transitions** | ChatGPT round 4 | Defense-in-depth coverage parallel to action="retire" |
| **2026-05-04 (effectiveness pass)** | **Add scope-choice protocol + mechanism specificity bar + anti-template list + ~~GOOD/BAD examples per scope~~ (SUPERSEDED by round 6 — replaced with valid-lesson rubric + invalid-lesson signals) + Phase 2 three-scope probes + Critical Rule 11 (ground in THIS quarter)** to learner SKILL.md spec | Claude fresh-read review (effectiveness lens) | Structural fields alone don't prevent generic prose. Round-6 update: concrete examples removed (LLM anchoring risk); replaced with abstract rubric + invalid signals |
| **2026-05-04 (effectiveness pass)** | **Concrete examples in §9.1 are ILLUSTRATIVE-only — learner must NEVER copy phrasings** | Claude (preserves existing T1 / U66 verbatim discipline) | Predictor's verbatim-only prompt (U66 in `prediction_learnerSkillsRedo.md`) already forbids template copying; the learner SKILL.md inherits this discipline by stating "do NOT copy phrasings; YOUR lesson body must come from THIS quarter's specific evidence" |
| **2026-05-04 (round 5)** | ~~D21: Legacy v2 dispatch in recovery + success aggregator paths~~ — **SUPERSEDED by round 6 fresh-start** (cutover wipes pre-v3 files; recovery only encounters v3) | ChatGPT round 5 | Original purpose: handle pre-cutover v2 files in recovery without aborting. Round-6 made the dispatch unnecessary by wiping v2 entirely |
| **2026-05-04 (round 5)** | **D22: lesson_id collision assertion at every append/refinement** (round 6: "at migration" wording removed since fresh-start has no migration; D22 still active for appends + cutover empty-init verification) | ChatGPT round 5 | 10^-4 collision probability is non-zero; silent corruption of audit attribution is the worst failure mode. Loud fail beats silent collision |
| **2026-05-04 (round 5)** | **§9.1 narrowest-justified-scope framing + scope-trigger examples + "what did the market reweight THIS quarter" prompt** | ChatGPT round 5 | Refines my earlier scope-choice protocol with conservative bias toward narrower (over-broadening hurts MORE future predictions than under-routing). Adds concrete trigger lists per scope. |
| **2026-05-04 (round 5)** | **Live trading orientation note in §1** | ChatGPT round 5 | Plan structurally covers live (PIT plumbing + same-quarter guard + post-event aggregation), but didn't explicitly call out "this is for live trading, not just backtesting." Brief framing note added |
| **2026-05-04 (round 5)** | **§19 Implementation playbook for fresh-context implementer** | User request | Plan must be self-contained for a no-context bot to implement end-to-end |
| **2026-05-04 (round 6)** | **Drop concrete GOOD/BAD example blocks in §9.1 → replace with valid-lesson rubric + invalid-lesson signals** | User concern (over-prescription anchoring) | LLMs over-fit to specific examples; principles + rubrics generalize better. ChatGPT corroborated. Concrete AVGO/AI-mix/2s10s/FCF examples removed; rubric-only retained |
| **2026-05-04 (round 7 — implementation clarifications)** | **Explicit specs added for: append_*_lesson stamping responsibility (§6.3), `_routing_key_from_source` helper definition (§7.1), D22 insertion-site list (§7.1), `_register_replacement` full pseudocode (§7.2), recovery-path sibling-file load semantics (§7.2)** | ChatGPT round 7 | Architecture is final but implementation details were under-specified. Pinning these prevents fresh-context implementer from guessing on load-bearing pieces (where Python stamps lesson_id, how routing_key is derived, what refinement inherits, what recovery path loads) |
| **2026-05-04 (round 7 — footgun fixes)** | **Aggregator pseudocode bugs fixed**: (a) ticker-scope branch now passes `ticker_hint=auditor_ticker` to `_routing_key_from_source` (helper raises without it); (b) `_register_replacement` call now passes `parent_source_entry=source_entry` (required by signature) | ChatGPT round 7 | A literal-following implementer would have hit a TypeError at runtime. Pseudocode now internally consistent |
| **2026-05-04 (round 7 — archetype removal)** | **Removed prescriptive archetype hints from prompt-facing text** (mechanism field description, renderer placeholder, Phase 2 probes, scope-choice protocol). Replaced with neutral language: "the causal chain explaining why this lesson worked in THIS event"; scope-choice rules trimmed to abstract decision criteria. | User concern + ChatGPT round 7 | Earlier rounds removed concrete examples (AVGO/AI-mix/2s10s) but left archetype names ("investor base / structural feature / cycle position") that create the same template-gravity risk. LLM might force every mechanism into one of those buckets instead of discovering it from evidence. Neutral language defers mechanism articulation entirely to the LLM |
| **2026-05-04 (round 7 — provenance shape)** | **Resolved storage-shape ambiguity: provenance is FLAT, not nested.** §5.2 now specifies two row variants (ticker-scope inside quarter row inheriting flat outer fields; global-scope as flat top-level entries). `_register_replacement` and `append_*_lesson` write flat. Drops the inconsistent nested `source: {...}` block | Self-review found the conflict; ChatGPT round 8 prioritized | Existing `append_global_lessons` (orchestrator:1414-1430) writes flat; §7.5.1 same-quarter guard reads flat (`e.get("source_ticker")`); a nested layer would require updating ~5 read sites and would silently break routing, self-leak, and learner-path decoration |
| **2026-05-04 (round 7 — refinement invariant)** | ~~Ticker-scope refinement INVARIANT hard-error: raise `TickerScopeRefinementError` on mismatch~~ — **SUPERSEDED by round 8/9** (auditor_ticker is authoritative for ticker-scope routing_key by file-system construction; runtime invariant + error class removed) | ChatGPT round 8 | Original purpose: detect cross-ticker contamination. Round-8 realized the check was either tautological or required invasive plumbing; ticker lessons live in `learnings/ticker/{ticker}.json` so the routing_key IS the filename. Simplified |
| **2026-05-04 (round 7 — helper contracts)** | **Added §7.2.1 helper-function contracts table** with inputs / upsert key / locking / failure for `_apply_audit_ticker`, `_apply_audit_global`, `_append_lesson_row_to_ticker_quarter`, `_append_lesson_row_to_global`, `_content_matches` | ChatGPT round 8 | These were referenced but never specified; two implementers would produce different upsert semantics and locking. Short contracts settle ambiguity without bloating the plan |
| **2026-05-04 (round 7 — round-trip smoke)** | **Round-trip smoke clarified to 3 quarters or synthetic seed.** Fresh-start at Q3 has no priors → Q3 learn writes lessons but no audits; Q4 predict labels Q3 lessons; Q4 learn writes audits; Q5 bundle reflects audits. Test must span this OR seed synthetics | ChatGPT round 8 | One-quarter loop in earlier description didn't actually exercise audit_history → render path |
| **2026-05-04 (round 8 — final cleanup)** | **G3 production-gate description updated to match §12 (3-quarter / synthetic-seed)**, **fake fallback in `_register_replacement` removed** (auditor_ticker is now authoritative for ticker-scope routing_key — file-system construction, not a runtime check), **§7.5 transient policy updated to flat schema**, **E18 fixed to state refined lesson INHERITS scope+routing**, **§19.2 SKILL change description updated to "rubric-only / no concrete examples"** | ChatGPT round 9 | Five stale internal contradictions found in fresh-eyes pass; all patched. No architecture change — pure document hygiene |
| **2026-05-04 (round 9 — implementor-bot patches)** | **7 implementation gaps closed**: (1) aggregator pseudocode now matches §7.2.1 helper-contract signatures (derives ticker_path + source_quarter_label explicitly, doesn't pass bundle quarter-row dict); (2) success-path now explicitly loads sibling `prediction/result.json` + `context_bundle.json` JSON before D19/aggregator (was wrongly stated as "already loaded"); (3) v3 validator refactor structure pinned (§8.2): wrapper + `_validate_common_core` + `_validate_v3`; hook validator treats `lesson_audit` as structurally optional, D19 enforces full coverage; (4) storage schema_version string updates explicit in file map (orchestrator:1331 + 1424, v1→v2); (5) ticker-scope audit lookup tuple pinned: `(source_quarter_label, lesson_id)`; (6) E31 refinement multi-write atomicity: single flock acquisition; (7) E32 D19 errors merge into `prior_validation_errors` with `[cross-file]` prefix; PLUS filter-first-then-decorate ordering pin in §7.5.2; PLUS E33 result_md_renderer deferral documented; PLUS E34 backup-glob policy stated | Implementor bot fresh review + ChatGPT round 10 | Implementor bot identified ~10 places where a fresh implementer would have to guess. Most were specification gaps where pseudocode and contracts disagreed, or where existing-code state was misstated. None were architectural — all final-mile hygiene. Plan is now literal-implementable |
| **2026-05-04 (round 10 — final stale-line patch)** | **§8.2 wording corrected**: removed "legacy v2 (read-only)" — round 6 is v3-only fresh-start; common rules apply only to v3 path. **E33 renderer deferral expanded** with explicit follow-up estimate (~30 lines for `_render_lesson_audit_table` helper) for post-launch readability if needed. (ChatGPT's #1 about "concrete examples in §19.2" was a false positive — already says "rubric-only / NO concrete examples" at line 1714.) | ChatGPT round 10 doc-polish | Final stale-text sweep |
| **2026-05-04 (round 11 — atomicity + docstring fix)** | **(1) E31 atomicity wired into pseudocode**: aggregator routes global+refine through `_register_replacement` with `audit_entry` parameter; new helper `_apply_audit_and_append_global_atomic` (added to §7.2.1) does both writes under single flock acquisition. Aggregator skips separate `_apply_audit_global` call when refining global lesson. **(2) `_register_replacement` docstring fixed**: removed stale TickerScopeRefinementError / hard-error wording — auditor_ticker is authoritative for ticker-scope (round 8/9 design); no runtime invariant check | ChatGPT round 11 | Two real internal contradictions found: pseudocode showed two separate global writes (violating E31's single-flock invariant), and docstring still claimed a hard-error that the code intentionally removed |
| **2026-05-04 (round 6)** | **Drop backward compatibility — fresh-start cutover** | User green-light + ChatGPT corroboration | Existing data thin (2 ticker quarters + 6 global entries); not worth migration complexity. Cutover wipes library + v2 attribution result files; v3 starts on empty libraries. Removes: D7, D12, D21, B2 fix legacy branch, v2 validator dispatch, migration script, legacy str-fallback, predictor "Legacy lessons" rule, renderer "(not recorded)" path, G1 migration smoke (replaced with fresh-start smoke), G6 legacy lesson test |

---

## 16. Confidence (post-corrections)

| Aspect | Confidence | Increases if |
|--------|------------|--------------|
| Architectural soundness | **94%** | Two more rounds of cross-review unable to surface new blocking issues |
| PIT correctness | **96%** | B1 test passes + historical replay smoke confirms audit visibility per pit_cutoff |
| Lesson quality discipline | **75%** | Proven over 3+ real quarters that mechanism-required lessons stay grounded |
| Implementation feasibility | **88%** | Stacked commits + smoke between each |
| Cutover safety | **94%** | `.pre-v3-cutover-backup/` + dry-run on copy of actual library before production cutover |
| Threshold defaults | **65%** | 3+ quarters of real audit data informs tuning |
| Aggregator idempotency (success + recovery) | **92%** | E5 + D18 tests pass |
| Live mode correctness | **92%** | Same-quarter guard test + live re-run smoke |
| **Overall: ready to implement** | **91% post-corrections; 78% as v1** | Apply v2 corrections + green-light |

---

## 17. Quick-start (next-session resume)

If resuming after compaction:

1. Read **§1 Executive Summary** + **§4 Decisions Locked** (especially D17-D20) + **§13 Implementation Sequence**.
2. Verify env: `git status`, `git log --oneline -5`, then `cat learnings/ticker/AVGO.json | head -20` to confirm v1 schema present.
3. Run pre-work tests as regression baseline:
   ```bash
   venv/bin/python -m pytest \
     scripts/earnings/test_validate_attribution.py \
     scripts/earnings/test_render_learning_context.py \
     scripts/earnings/test_learning_context.py \
     scripts/earnings/test_finalize_session_id_preservation.py \
     -q --no-header
   ```
4. Execute commits 1→2→3→4 per §13.
5. Run AVGO Q4 historical smoke; inspect `learning/result.json` for v3 schema, library files for audit_history; visual-confirm bundle render shows mechanism + reviews badges (no legacy fallback rendering — round 6 fresh-start).
6. One cross-sector smoke (CRM Q4 or BURL).

**Rollback**: per-file `git checkout HEAD~N -- <file>`. Library + attribution files restored from `.pre-v3-cutover-backup/` per §10.2 backup procedure. Do NOT use `git reset --hard` (working tree carries unrelated dirty work).

---

## 18. Appendix — review history

This plan went through **3 rounds of cross-review** between Claude and ChatGPT before being locked. Key decisions and the source/round of each are preserved in §15 Decision log. The summary:

- **Round 1**: Claude proposed prose-only MVP (§13.18 of `prediction_learnerSkillsRedo.md`); ChatGPT critiqued as too weak for self-healing.
- **Round 2 — v1 of this file**: Claude proposed structured + closed-loop architecture (3 pillars + lesson-centric storage); ChatGPT pushed back on full storage flatten and refined review enum from 4 to 6 values.
- **Round 3 — this v2 file**: Both reviewers found additional issues. Claude found B1 (audit-history future leak), B2 (legacy lifecycle), B3 (evidence_refs cross-check). ChatGPT found D17 (compute-only status), D18 (recovery-path aggregator), D19 (orchestrator-level cross-file validation), D20 (renderer body-only). All merged into this v2.
- **Round 4 — this update**: ChatGPT independently re-reviewed v2 and confirmed all 8 substantive corrections (B1, B2, B3, D17, D18, D19, D20, N1, N3) were correctly captured. ChatGPT flagged one apparent gap — `compute_status` not treating `action="refine"` as terminal — which was actually already in v2 line 550 (ChatGPT was reviewing v1 logic). The substantively new content from round 4 is **§13.5 production verification gates (10 tests)** with G2 (historical PIT leak) and G3 (full-loop smoke) hard-gated for ship.
- **Round 5 — this update**: Final compatibility & polish pass. ChatGPT flagged D21 (v2 legacy handling in aggregator/cross-file dispatch — real bug; v2 files would fail D19), D22 (lesson_id collision assertion — defensive, addresses ~10^-4 collision), and a sharper SKILL.md framing ("narrowest justified scope" + "what did the market reweight THIS quarter" + per-scope trigger lists). All adopted. Live-trading orientation note added to §1. Implementation playbook added as §19 for fresh-context implementer self-sufficiency.

The earlier discussion (raw transcripts of rounds 1 and 2) was preserved in v1 of this file; v1 is recoverable via `git log --oneline LearnerLoopRevamp.md` (commit prior to 2026-05-04 v2 update).

---

## 19. Implementation playbook (fresh-context implementer)

This section is the definitive checklist for an implementer with no prior conversation context. Read §1, §4, §13, then this. Everything load-bearing is referenced here.

### 19.1 Before writing code

```bash
cd /home/faisal/EventMarketDB

# Confirm working tree is clean of unrelated dirty changes
git status --short
# Expect mostly deleted test agents and a couple of plan/skill mods —
# DO NOT bundle those with this work.

# Regression baseline (must stay green after each commit)
venv/bin/python -m pytest \
  scripts/earnings/test_validate_attribution.py \
  scripts/earnings/test_render_learning_context.py \
  scripts/earnings/test_learning_context.py \
  scripts/earnings/test_finalize_session_id_preservation.py \
  scripts/earnings/test_orchestrator_paths_u65.py \
  scripts/earnings/test_validate_prediction_result.py \
  -q --no-header

# Confirm pre-cutover library state (will be wiped per §10.2)
ls -la earnings-analysis/learnings/ticker/AVGO.json earnings-analysis/learnings/global.json 2>/dev/null || echo "(library already empty — fine for first run)"
```

### 19.2 Files affected (complete map)

**Touched (existing — modifications)**:
| File | What changes |
|------|--------------|
| `scripts/earnings/validate_learning.py` | Add v3 schema branch (§8.3); evidence_refs ID resolution (B3) |
| `scripts/earnings/earnings_orchestrator.py` | (a) `aggregate_lesson_audits` function (§7.2); (b) `compute_status` function (§7.3); (c) `compute_lesson_id` + `assert_no_id_collision` (§7.1); (d) `_passes_audit_pit` helper + audit-history PIT filter in `build_learning_context` (§7.5.2); (e) same-quarter self-leak guard for both ticker + global (§7.5.1); (f) `_validate_audit_against_prediction` cross-file gate (§7.6); (g) schema-version dispatch on insertion sites; (h) wire aggregator into success path (~line 1281) AND recovery path (lines 1162-1167) per D18; (i) **storage schema_version string updates** — change `"ticker_lessons.v1"` → `"ticker_lessons.v2"` at orchestrator:1331 in `append_ticker_lesson` skeleton init AND change `"global_lessons.v1"` → `"global_lessons.v2"` at orchestrator:1424 in `append_global_lessons` skeleton init; (j) **explicit sibling-file load** in success path before D19/aggregator (paths exist at orchestrator:1199-1200; need explicit `json.loads`); (k) **filter-first-then-decorate ordering** in `build_learning_context` — call `_apply_render_view` (PIT-filter audits + compute status + drop retired) BEFORE `_decorate_with_learner_paths` so the allowlist excludes retired lessons |
| `scripts/earnings/_text_utils.py` | `iter_labeled_lessons` skips lessons whose transient `_render_status == "retired"` (§7.4); v3 dict-only body resolution (round 6: removed v1 str-fallback) |
| `scripts/earnings/renderer/lessons.py` | Render mechanism / applies_when / invalid_if / status badge / reviews summary (§7.4); ordered_lesson_texts is BODY ONLY (D20) |
| `.claude/skills/earnings-learner/SKILL.md` | Phase 1 step 4.5 (read predictor labels); Phase 2 three-scope probes; Phase 4 structured-output rules + scope-choice protocol + mechanism specificity bar + anti-template list + valid-lesson rubric + invalid-lesson signals (round 6: NO concrete examples — rubric-only to avoid LLM anchoring); Critical Rules 9, 10, 11 (§9.1) |
| `.claude/skills/earnings-prediction/SKILL.md` | §3.3 add mechanism gate + track record signal + lesson_text discipline (§9.2) |

**Created (new)**:
| File | Purpose |
|------|---------|
| ~~`scripts/migrate_learnings_v1_to_v2.py`~~ | **REMOVED** (round 6 fresh-start). Cutover is one-shot bash wipe in §10.2 |
| `scripts/earnings/test_validate_learning_v3.py` | v3 schema validation tests including evidence_refs cross-resolution (B3) |
| `scripts/earnings/test_aggregate_lesson_audits.py` | Aggregator success + recovery + idempotency tests (D18) |
| `scripts/earnings/test_lesson_status_transitions.py` | compute_status pure-function table (D6 + D17 + B2 + refine-terminal) |
| `scripts/earnings/test_audit_history_pit_filter.py` | B1 future-leak regression test |
| ~~`scripts/earnings/test_legacy_lesson_lifecycle.py`~~ | **REMOVED** (round 6 fresh-start) |
| `scripts/earnings/test_evidence_refs_resolve.py` | B3 phantom-ID rejection |
| `scripts/earnings/test_aggregator_recovery_path.py` | D18 recovery path runs aggregator |
| `scripts/earnings/test_orchestrator_cross_file_validation.py` | D19 mismatches trigger H2 retry |
| `scripts/earnings/test_lesson_id_stability.py` | D10 + D22 collision assertion |
| ~~`scripts/earnings/test_migrate_learnings_v1_to_v2.py`~~ | **REMOVED** (round 6 fresh-start) |
| `scripts/earnings/test_render_lessons_v2.py` | New rendering + status badge + CAUTION prefix on watch |
| `scripts/earnings/test_pit_self_leak_guard.py` | D13 same-quarter exclusion (ticker + global) |
| `scripts/earnings/test_iter_labeled_lessons_v2.py` | Skip retired (`_render_status` transient); v3-dict-only |
| `scripts/earnings/test_loop_round_trip_smoke.py` | N4 end-to-end loop |

**NOT TOUCHED — DO NOT EDIT**:
- `validate_prediction_result.py` (predictor T1 logic stays unchanged; v3 lesson_dicts still yield body-only `expected_lesson_texts`)
- `.claude/hooks/validate_learning_output.py` (hook calls `validate_attribution_result`; schema-version dispatch handled inside)
- All bundle builder files (`builders/*.py`) — bundle assembly is unchanged
- Renderer files outside `lessons.py` — no other section affected
- `learnings/global.json` flock pattern (already correct; reuse)

### 19.3 Commit-by-commit go/no-go

After EACH commit, run the regression baseline (§19.1). If it fails, halt and investigate before proceeding. Do not stack commits onto a broken baseline.

| Commit | Pre-condition | Acceptance criteria |
|--------|---------------|---------------------|
| 1 (validator) | Baseline green | New tests in `test_validate_learning_v3.py` + `test_evidence_refs_resolve.py` pass; v2 tests still green; v3 dispatch works |
| 2 (orchestrator) | Commit 1 merged | All §12 tests green (lesson_status, aggregator, audit-history-pit, recovery, cross-file, lesson_id, self-leak, iter); regression baseline still green |
| 3 (renderer) | Commit 2 merged | `test_render_lessons_v2.py` green; renderer goldens regenerated and reviewed; T1 positional check still passes against v2 lesson_dicts |
| 4 (skills + cutover) | Commit 3 merged | `test_loop_round_trip_smoke.py` green; SKILL.md changes reviewed; cutover bash from §10.2 dry-run on a COPY of `learnings/` and `events/*/learning/` first |
| Cutover | Commit 4 merged + all tests green | Run §10.2 cutover bash against actual `learnings/` + `events/*/learning/`; verify `.pre-v3-cutover-backup/` written; verify wiped state |

### 19.4 Production verification (after all commits + cutover)

Run §13.5 gates in order. Must pass G1, G2, G3, G4, G5, G7, G10 to ship (minimum gate — 7 of 9 active gates; G6 was removed in round 6 as legacy lesson test no longer applies after fresh-start cutover). Preferred to pass all 9 active gates (G1-G5, G7-G10). **DO NOT SHIP without G2 and G3 passing.**

### 19.5 Rollback procedure

Per-file rollback only. **NEVER `git reset --hard`** — working tree carries unrelated dirty work.

```bash
# Revert a specific file to last-good commit
git checkout <last-good-commit> -- scripts/earnings/<file>

# Restore library + attribution files from cutover backup (round 6)
cp -a earnings-analysis/.pre-v3-cutover-backup/learnings/ \
      earnings-analysis/learnings/
# Attribution result files were also wiped by cutover; restore from backup tree
find earnings-analysis/.pre-v3-cutover-backup/Companies -name "result.json" \
  | while read f; do
      rel=$(echo "$f" | sed 's|.pre-v3-cutover-backup/||')
      mkdir -p "$(dirname "$rel")"
      cp "$f" "$rel"
    done
```

### 19.6 Reference: full list of "where does X live?"

| Concept | Lives at |
|---------|----------|
| Lesson schema spec | §5.2 |
| Learner output schema (v3) | §5.1 |
| Storage shapes (ticker.json + global.json) | §6 |
| Aggregator algorithm | §7.2 |
| `compute_status` pure function | §7.3 |
| Renderer rendering rules | §7.4 |
| PIT guards (lesson + audit-history) | §7.5 |
| Cross-file validation | §7.6 |
| Validator changes | §8 |
| SKILL.md changes | §9 |
| Migration plan | §10 |
| Edge cases | §11 |
| Test specifications | §12 |
| Tunable constants | §14 |
| Production gates | §13.5 |

### 19.7 Common pitfalls a fresh implementer should avoid

1. **Don't store `status` to disk.** It's computed at render time (D17). Library files have only audit_history.
2. **Don't `git reset --hard`** anywhere. Use file-scoped checkout.
3. **Don't skip the same-quarter guard.** It applies to BOTH ticker_lessons and global_lessons (D13).
4. **Don't skip the audit-history PIT filter.** Without it, replays leak future audits (B1).
5. **Don't write `_render_status` / `_render_audit_counts` to library files** — they're transient render-time only.
6. **Don't change `iter_labeled_lessons` signature** without updating renderer + validator's expected_lesson_texts derivation. The function is shared.
7. **Don't merge commits 1-4 into one.** They're stacked for reviewability + per-commit smoke. Land sequentially.
8. **Don't run §10.2 cutover bash on production `learnings/` + `events/*/learning/` until tests pass on a COPY first.**
9. **Don't add legacy v2 read-compat back.** Round 6 fresh-start removed all v2 paths; reintroducing them re-imports the stale-data risks.
10. **Don't skip the lesson_id collision assertion (D22).** Silent collision is the worst failure mode.
