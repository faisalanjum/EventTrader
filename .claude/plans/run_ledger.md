# Run Ledger — Production-Ready Lifecycle Index for Pipeline Runs

**Status**: LOCKED — reviewed, validated, all blockers addressed. Ready to implement in one atomic commit.

**Date**: 2026-04-19

**Scope**: Guidance extraction + prediction + learner. Three pipelines, one ledger, one human-facing index note.

---

## 1. Problem Statement

The repo has three production pipelines that produce derived artifacts under
`earnings-analysis/`:

| Component | Runtime | Writes |
|---|---|---|
| **guidance** | `scripts/extraction_worker.py` (K8s, 1→7 pods) | Guidance nodes in Neo4j + hook notes in `pipeline/extractions/guidance/*.md` + harvester thinking shards |
| **prediction** | `scripts/earnings/earnings_orchestrator.py --predict` | `events/{Q}/prediction/{result.json, result.md, thinking.md}` + subagents/ |
| **learning** | `scripts/earnings/earnings_orchestrator.py --learn` | `events/{Q}/learning/{result.json, result.md, thinking.md}` + subagents/ |

**Gaps the completed-artifact surfaces do NOT cover**:

1. **No real-time lifecycle state.** `result.md` and `thinking.md` only exist AFTER success. There's no way to see queued/running/failed jobs from the vault.
2. **No cross-pipeline browsable index.** Reviewers have to walk the file tree to enumerate recent runs across all three types.
3. **Legacy CSV trackers** (`earnings-analysis/predictions.csv`, `prediction_processed.csv`) are ad-hoc, prediction-only, and don't scale to a 796-ticker universe.

The old `pipeline/extractions/Extraction Runs.md` was a Dataview index note (renders from per-extraction-note frontmatter). It worked for extractions but was never extended to prediction/learner and didn't cover in-flight state.

---

## 2. Design Principles

1. **Separation of concerns**: machine-readable state (JSONL ledger) vs human-readable view (Markdown index). Ledger is authoritative; index is a rendering.
2. **Append-only** machine store. Each state transition = one new line. Current state = last-row-wins collapse by `run_id`. No in-place mutations.
3. **Wrap real execution boundaries**, not post-hoc finalizers. `open_run` fires BEFORE the SDK call; `close_run` fires on terminal state. A running job is observable as `status="running"` from the moment it starts.
4. **Crash-safe**: tolerate malformed JSONL lines (skip silently); atomic writes (tmp + rename) for the index note.
5. **Plugin-independent**: no Dataview dependency. Index is Python-generated static Markdown tables.
6. **Minimal code, frozen schema v1**. No per-run Markdown mirror notes. No artifact frontmatter changes.

---

## 3. Architecture — Three Layers

### Layer 1 — Authoritative Ledger

```
earnings-analysis/operations/run_ledger.jsonl
```

Append-only JSONL. Each line = one state transition.

**Size budget**: ~7,500 runs/year at production scale × ~500 bytes/row × 5 years ≈ **18 MB**.
Single file for v1. Document rotation trigger: rotate to `run_ledger_YYYY.jsonl`
when file exceeds 50 MB.

### Layer 2 — Human-Facing Index Note

```
earnings-analysis/operations/Run Index.md
```

Single Markdown file. Python-generated static tables. Four sections:

```markdown
# Run Index
_Last regenerated: <ISO timestamp>_

## In Flight (status == running)
| run_id | component | ticker | quarter | started_at |
| ... | ... | ... | ... | ... |

## Recent Predictions (last 50 by started_at DESC)
| date | ticker | quarter | direction | conf | magnitude | expected | status | run_id |
| ... |

## Recent Learners (last 50)
| date | ticker | quarter | direction_correct | actual_return | magnitude_error | primary_driver | status | run_id |
| ... |

## Recent Extractions (last 50)
| date | ticker | asset | source_id | items_extracted | items_written | enrichment | status | run_id |
| ... |
```

Regenerated on BOTH `open_run` and `close_run` — otherwise In Flight is always empty.

Atomic write via `write tmp + os.replace` — crash during regeneration never leaves a half-written index.

### Layer 3 — (Not Needed in v1)

No per-run Markdown mirror notes. No artifact frontmatter changes.
Artifacts already carry `sdk_session_id` which provides a cross-lookup key.

---

## 4. Ledger Schema (frozen v1)

Every row is a complete state snapshot for one `(run_id, transition)`. Reader
collapses by `run_id`, last-row-wins.

```json
{
  "schema_version": 1,
  "run_id": "uuid4-string",
  "component": "guidance | prediction | learning",
  "status": "running | succeeded | failed | skipped | rate_limited",
  "ticker": "BURL",
  "quarter_label": "Q3_FY2025",
  "accession_8k": "0001193125-25-294501",
  "source_id": null,
  "source_asset": null,
  "experiment_name": null,
  "sdk_session_id": null,
  "started_at": "2026-04-19T12:34:56Z",
  "finished_at": null,
  "elapsed_seconds": null,
  "artifact_dir": null,
  "result_path": null,
  "thinking_path": null,
  "error": null,
  "summary": {}
}
```

### Per-component `summary` payloads

**prediction**:
```json
{
  "direction": "long|short|no_call",
  "confidence_score": 68,
  "confidence_bucket": "low|moderate|high|extreme",
  "magnitude_bucket": "small|medium|large",
  "expected_move_range_pct": [3.0, 6.5]
}
```

**learning**:
```json
{
  "direction_correct": false,
  "actual_daily_stock_pct": -12.16,
  "magnitude_error_pct": 15.16,
  "primary_driver_category": "peer_comp_gap_share_loss"
}
```

**guidance**:
```json
{
  "items_extracted": 14,               // primary_items from the combined result file
  "items_written": 14,                 // len() of /tmp/gu_written_<source_id>.json (authoritative)
  "enrichment_status": "enriched",     // enum: "enriched" | "no_enrichment" | "no_primary" | null
  "items_enriched": 3,                 // audit-only — renderer ignores
  "items_new_secondary": 2             // audit-only — renderer ignores
}
```

The `items_written` sidecar is written by `.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py` as a list of per-item audit entries; `len(list)` is authoritative for the Neo4j write count. `extraction_worker.process_one` unlinks any prior sidecar at entry (stale-guard) so a read here always reflects the current attempt.

The `enrichment_status` enum is derived purely from the combined result file counts (no external state):
  * `"no_primary"` — `primary_items == 0` (nothing to enrich)
  * `"no_enrichment"` — `primary_items > 0` but `enriched_items + new_secondary_items == 0`
  * `"enriched"` — at least one enriched or new secondary item
  * `null` — all counts absent (unknown; don't fabricate)

### Status values (all five explicit)

| Status | Meaning | Terminal? |
|---|---|---|
| `running` | `open_run` fired; SDK call in progress | No |
| `succeeded` | Run produced expected artifacts | Yes |
| `failed` | Run raised an exception or produced no result | Yes |
| `skipped` | Run deliberately not executed (e.g., preconditions unmet) | Yes |
| `rate_limited` | SDK hit API rate limit; payload was requeued for future attempt. **A new run_id is issued on retry.** | Yes (this attempt) |

Each attempt = new `run_id`. Retries don't reuse the previous run_id — audit trail stays clean.

---

## 5. Concurrency + Safety

### Writes

```python
def append(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with open(path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
```

**Safe for**: multiple processes on the same host accessing the same file
(e.g., K8s extraction-worker 1→7 pods via hostPath mount to a single node).

**NOT safe for**: NFS, distributed filesystems with weak locking, or
cross-host access. Document this explicitly in the module docstring.

**Rationale**: POSIX does NOT guarantee atomic appends for regular files
regardless of write size. PIPE_BUF (4096) only applies to pipes/FIFOs.
`fcntl.flock` + `fsync` provides correct coordination on a single-host
shared filesystem.

### Reads

```python
def read_all(path):
    if not path.exists():
        return []
    rows = []
    with open(path) as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # tolerate torn writes from crashed writers
    return rows
```

Tolerating malformed lines preserves readability across crash windows.

### Index atomic write

```python
def _write_atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
```

---

## 6. Public API

Module: `scripts/earnings/run_ledger.py`

```python
def open_run(
    component: str,                      # "guidance" | "prediction" | "learning"
    *,
    ticker: str,
    quarter_label: str | None = None,
    accession_8k: str | None = None,
    source_id: str | None = None,
    source_asset: str | None = None,
    experiment_name: str | None = None,
    artifact_dir: str | None = None,
) -> str:
    """Append a `running` row. Returns new run_id (uuid4)."""


def close_run(
    run_id: str,
    status: str,                         # "succeeded" | "failed" | "skipped" | "rate_limited"
    *,
    sdk_session_id: str | None = None,
    result_path: str | None = None,
    thinking_path: str | None = None,
    error: str | None = None,
    summary: dict | None = None,
) -> None:
    """Append a terminal row for an existing run_id. Also refreshes Run Index.md."""


def current_state(
    *,
    component: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Collapse ledger by run_id (last-row-wins); apply filters; return list."""


def refresh_index(
    ledger_path: Path | None = None,
    index_path: Path | None = None,
) -> None:
    """Read ledger, build Run Index.md content, atomic-write to index_path."""
```

Each `open_run` and `close_run` call triggers `refresh_index` synchronously.
This guarantees real-time visibility — the moment a run starts, it appears
in the In Flight section.

---

## 7. Call-Site Wiring (exact execution boundaries)

**Design rule (critical)**: wrap the OUTERMOST meaningful function boundary,
NOT individual SDK `query()` calls. One ledger run = one logical pipeline
attempt. Internal retries, derived-write recovery, validation, and
side-effect writes (result.md, lesson appends) must all resolve BEFORE the
terminal close_run fires. Otherwise the ledger can record a false success
when a post-SDK step raises.

### Prediction — wraps SDK + finalize + validate in one try block

Location: `earnings_orchestrator.py` inside `if args.predict:` block (line 3181).
Wraps everything from the `query()` loop through `validate_prediction_result()`.

```python
run_id = run_ledger.open_run(
    "prediction",
    ticker=args.ticker, quarter_label=ql, accession_8k=acc,
    artifact_dir=str(paths["result_path"].parent),
)
try:
    # 1. SDK query loop — captures session_id, drives to completion
    async for msg in query(prompt=prompt, options=options):
        ...

    # 2. result_path must exist
    if not paths["result_path"].exists():
        raise RuntimeError("Predictor finished without writing result.json")

    # 3. finalize — writes result.md + harvests thinking.md (may raise)
    finalize_prediction_result(...)

    # 4. read result.json
    with open(paths["result_path"], encoding="utf-8") as f:
        prediction = json.load(f)

    # 5. validate — raises on schema mismatch
    validate_prediction_result(
        prediction,
        expected_ticker=args.ticker,
        expected_quarter=quarter_info["quarter_label"],
    )

    # Only now are we truly succeeded
    run_ledger.close_run(
        run_id, "succeeded",
        sdk_session_id=predictor_session_id,
        result_path=str(paths["result_path"]),
        thinking_path=str(paths["result_path"].parent / "thinking.md"),
        summary={
            "direction": prediction["direction"],
            "confidence_score": prediction["confidence_score"],
            "confidence_bucket": prediction["confidence_bucket"],
            "magnitude_bucket": prediction["magnitude_bucket"],
            "expected_move_range_pct": prediction["expected_move_range_pct"],
        },
    )
except Exception as e:
    run_ledger.close_run(run_id, "failed", error=str(e)[:500])
    raise
```

### Learner — wraps the WHOLE `run_learner_for_quarter()` function

Location: `earnings_orchestrator.py` inside `if args.learn:` block, around the
`run_learner_for_quarter(...)` call. This is the natural unit of "one learner
run" — the function handles SDK invocation, derived-write recovery (no SDK
call at all if `learning/result.json` already exists), validation retry
(up to 2 SDK calls), and lesson appends to `learnings/ticker/*.json` +
`learnings/global.json`. All of that is ONE ledger run.

**Contract change (2026-04-19)**: `run_learner_for_quarter` returns
`tuple[dict | None, str]` where the second element is a
:class:`LearnerOutcome` string constant. This lets the caller distinguish
*skipped* (environmental — event not ready to learn from) from *failed*
(pipeline-level error) from *succeeded/recovered*. Before this change the
caller recorded every `None` return as `"failed"`, which polluted the audit
trail with phantom failures for quarters that had no prediction yet or no
published stock-price — neither is a defect.

```python
class LearnerOutcome:
    SUCCEEDED                 = "succeeded"
    RECOVERED                 = "recovered"        # derived-write recovery hit valid existing
    SKIPPED_NO_PREDICTION     = "skipped_no_prediction"
    SKIPPED_NO_DAILY_STOCK    = "skipped_no_daily_stock"
    FAILED_NO_RESULT          = "failed_no_result"
    FAILED_INVALID_JSON       = "failed_invalid_json"
    FAILED_NO_RESULT_RETRY    = "failed_no_result_retry"
    FAILED_INVALID_JSON_RETRY = "failed_invalid_json_retry"
    FAILED_VALIDATION         = "failed_validation"
    FAILED_RECOVERY_APPEND    = "failed_recovery_append"
    FAILED_TICKER_APPEND      = "failed_ticker_append"
    FAILED_GLOBAL_APPEND      = "failed_global_append"

    SUCCESS = frozenset({SUCCEEDED, RECOVERED})
    SKIPPED = frozenset({SKIPPED_NO_PREDICTION, SKIPPED_NO_DAILY_STOCK})
    FAILED  = frozenset({FAILED_NO_RESULT, FAILED_INVALID_JSON,
                         FAILED_NO_RESULT_RETRY, FAILED_INVALID_JSON_RETRY,
                         FAILED_VALIDATION, FAILED_RECOVERY_APPEND,
                         FAILED_TICKER_APPEND, FAILED_GLOBAL_APPEND})
    ALL = SUCCESS | SKIPPED | FAILED   # 12 members — one per return site
```

All 12 return sites in `run_learner_for_quarter` are tagged 1:1 with a
constant; `test_learner_outcomes.py` asserts `len(ALL) == 12`, the three
category sets are pairwise disjoint, and their union is `ALL` — so adding a
new return branch without categorizing it fails the test suite loudly.

```python
run_id = run_ledger.open_run(
    "learning",
    ticker=args.ticker, quarter_label=target_ql, accession_8k=target_acc,
    artifact_dir=str(COMPANIES_DIR / args.ticker.upper() / "events"
                     / target_ql / "learning"),
)
try:
    attribution, outcome = run_learner_for_quarter(
        ticker=args.ticker,
        quarter_info=quarter_info,
        events=events,
        current_index=current_index,
        pit_mode="historical",
        live_state_path=live_state_path,
    )
    if outcome in LearnerOutcome.SUCCESS:
        # SUCCEEDED or RECOVERED — both produce a valid attribution dict.
        pd = attribution.get("primary_driver", {}) or {}
        fb = attribution.get("feedback", {}) or {}
        pc = fb.get("prediction_comparison", {}) or {}
        ar = attribution.get("actual_return", {}) or {}
        run_ledger.close_run(
            run_id, "succeeded",
            sdk_session_id=attribution.get("sdk_session_id"),
            result_path=str(learning_dir / "result.json"),
            thinking_path=str(learning_dir / "thinking.md"),
            summary={
                "direction_correct":       pc.get("direction_correct"),
                "magnitude_error_pct":     pc.get("magnitude_error_pct"),
                "primary_driver_category": pd.get("category"),
                "actual_daily_stock_pct":  ar.get("daily_stock_pct"),
            },
        )
    elif outcome in LearnerOutcome.SKIPPED:
        # Environmental — not a defect. Outcome string IS the diagnostic.
        run_ledger.close_run(run_id, "skipped", error=outcome)
    else:
        # Must be FAILED (enforced by invariant test).
        run_ledger.close_run(run_id, "failed", error=outcome)
except Exception as e:
    run_ledger.close_run(run_id, "failed", error=str(e)[:500])
    raise
```

The summary fields exactly match the four keys read by
`run_ledger.py::_render_learners_section` (`direction_correct`,
`magnitude_error_pct`, `primary_driver_category`, `actual_daily_stock_pct`).
Test `test_run_ledger.py::test_16_learner_summary_has_exactly_the_four_renderer_keys`
pins this contract.

**Caller migration**: 4 other callers exist (`scripts/run_phase4_big.py`,
`scripts/run_calibration_sequential.py`,
`scripts/run_q3_from_existing_bundle.py`, `scripts/calibrate_learner.py`).
Each one just needs the tuple unpack: `result, _ = run_learner_for_quarter(...)` —
their existing `if not result:` / `if attribution:` logic keeps working
because the first element is still `dict | None`.

### Guidance — wraps INSIDE `process_one()`, per-exit close

Location: `scripts/extraction_worker.py`, at the top of `process_one` (open)
and at every return path (close). The earlier "wrap outside in the main
loop" approach was rejected because the outer wrapper has no access to the
concrete `result_path`, `result_data`, `result_msg.usage`, or the write-CLI
sidecar — all of which are locals inside `process_one`. An outer wrap could
only guess with wildcard paths and null-valued summaries.

**Ledger is gated**: only opened for `type_name in VALID_COMPONENTS` (i.e.
currently only `"guidance"`). Other extraction types (sentiment, etc.) skip
the ledger entirely — they don't belong in the guidance section of the
index.

**Stale-sidecar guard**: `/tmp/gu_written_{source_id}.json` is written by
`.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py:647` and
is NOT cleaned up by the write CLI, the obsidian hook, or any prior code.
`process_one` unlinks it at entry (gated on `type_name == "guidance"`) so a
later peek only sees items the current attempt wrote. Without this guard, a
dry_run attempt following a write-mode attempt would inherit the prior
attempt's count.

```python
async def process_one(ticker, asset, source_id, type_name, mode, mgr) -> bool | str:
    # 1. Open ledger (gated)
    ledger_run_id = None
    if type_name in _LEDGER_COMPONENTS:  # {"guidance", "prediction", "learning"}
        try:
            ledger_run_id = _ledger_open(type_name, ticker=ticker,
                                         source_id=source_id, source_asset=asset)
        except Exception:
            ledger_run_id = None

    def _close_ledger(status, *, error=None, summary=None):
        if not ledger_run_id: return
        try: _ledger_close(ledger_run_id, status, error=error, summary=summary)
        except Exception: pass

    # 2. Stale-sidecar guard (guidance-specific)
    if type_name == "guidance":
        Path(f"/tmp/gu_written_{source_id}.json").unlink(missing_ok=True)

    # 3. ... existing SDK query loop + result-file handling ...

    # 4. On each exit:
    # rate_limited:
    _close_ledger("rate_limited");  return "rate_limited"
    # various failures:
    _close_ledger("failed", error=<specific reason>);  return False
    # success:
    _close_ledger("succeeded", summary=_build_guidance_summary(
        source_id=source_id, result_data=result_data, result_msg=result_msg))
    return True
```

**Summary builder** (pure, unit-testable):

```python
def _build_guidance_summary(*, source_id, result_data, result_msg) -> dict:
    rd = result_data or {}
    primary_items       = rd.get("primary_items")
    enriched_items      = rd.get("enriched_items")
    new_secondary_items = rd.get("new_secondary_items")

    # items_written from the fresh-guaranteed sidecar
    items_written = None
    gw = Path(f"/tmp/gu_written_{source_id}.json")
    if gw.exists():
        try:   items_written = len(json.loads(gw.read_text()))
        except Exception:  items_written = None

    # enrichment_status enum (never fabricate)
    if primary_items is None and enriched_items is None and new_secondary_items is None:
        enrichment_status = None
    elif primary_items == 0:
        enrichment_status = "no_primary"
    elif (enriched_items or 0) + (new_secondary_items or 0) == 0:
        enrichment_status = "no_enrichment"
    else:
        enrichment_status = "enriched"

    return {
        "items_extracted":     primary_items,
        "items_written":       items_written,
        "enrichment_status":   enrichment_status,
        "items_enriched":      enriched_items,        # audit-only
        "items_new_secondary": new_secondary_items,   # audit-only
    }
```

**Critical semantics**:
- `rate_limited` is a TERMINAL state for this attempt. A retry is a NEW `run_id`.
- Each attempt appears distinctly in the audit trail: "3 rate_limited
  attempts at 10:00/10:05/10:10, then succeeded at 10:15" = 4 rows,
  4 run_ids.
- `enrichment_status` is always one of the 4 values documented in §2
  (never free-text, never fabricated counts).
- The per-exit close inside `process_one` is deliberate: the outer `main()`
  loop only routes the `outcome` for retry / dead-letter decisions and has
  no access to the execution-level details the ledger wants.

---

## 8. Run Index Rendering

### Section order
1. In Flight (status == running)
2. Recent Predictions (component == prediction, last 50 by started_at DESC)
3. Recent Learners (component == learning, last 50)
4. Recent Extractions (component == guidance, last 50)

### Column specifications

**In Flight** — compact, no per-component columns
| run_id | component | ticker | quarter | started_at | elapsed |

**Predictions**
| date | ticker | quarter | direction | conf | magnitude | expected | status | run_id |

**Learners**
| date | ticker | quarter | direction_correct | actual_return | magnitude_error | primary_driver | status | run_id |

**Extractions**
| date | ticker | asset | source_id | items_extracted | items_written | enrichment | status | run_id |

### Format conventions

- `date`: YYYY-MM-DD (extracted from started_at)
- `run_id`: first 8 chars (full id in ledger)
- `expected`: `"{low}–{high}%"` string
- `status`: emoji-decorated (✅ succeeded / ❌ failed / 🔄 running / ⏸ rate_limited / ⏭ skipped)
- Empty cells rendered as `—` (em-dash)

---

## 9. Corrections Accepted from Review

All four blocker issues from the first-round review:

1. ✅ **Dataview-JSONL mismatch fixed** — Python generates static Markdown tables; no Dataview dependency.
2. ✅ **Execution boundary is correct** — `open_run` wraps the SDK `query()` call, not `finalize_*_result()`.
3. ✅ **POSIX safety is correctly stated** — `fcntl.flock(LOCK_EX) + flush + fsync` on a single-host shared FS. No PIPE_BUF claim.
4. ✅ **Single path, `component` in schema, internally consistent.**

Plus three trims from the second-round review:

1. ✅ **Real-time requires refresh on open AND close.** Index is regenerated on every state transition — not just terminal.
2. ✅ **`rate_limited` status is explicit** — mapped from extraction_worker's requeue branch; audit trail shows every attempt distinctly.
3. ✅ **`run_id` NOT added to artifact frontmatter in v1.** Ledger carries `result_path`/`thinking_path`; artifacts carry `sdk_session_id`. Cross-reference is already possible.

---

## 10. Scope / File-Level Impact

| File | Action | Lines |
|---|---|---|
| `scripts/earnings/run_ledger.py` | **NEW** — append + read + collapse + refresh_index with atomic write | ~120 |
| `scripts/earnings/test_run_ledger.py` | **NEW** — 15 tests | ~220 |
| `scripts/earnings/earnings_orchestrator.py` | wrap prediction SDK call (~line 3044) + wrap learner SDK call | +~25 |
| `scripts/extraction_worker.py::process_one` | wrap execution + rate_limited branch | +~15 |
| `earnings-analysis/operations/` | **NEW DIR**. `Run Index.md` seeded as an empty 4-section stub. `run_ledger.jsonl` is lazy-created on the first `_append_row` call — empty files are noise and the open/close primitives already `mkdir(parents=True, exist_ok=True)`. | — |

**Net**: ~140 lines of new code + ~40 lines modifications + 15 tests + 2 new vault files.

No frontmatter schema changes. No new runtime dependencies. No touching
existing CSVs (deprecate after 90 days of ledger being live).

---

## 11. Tests (exactly 15)

**Primitives**
1. `append` writes a valid JSON line ending with `\n`
2. Reader skips malformed JSON lines silently (simulated torn writes)
3. Concurrent writers (20-thread pool) produce zero corrupted lines
4. Missing ledger file → `current_state()` returns `[]` (no error)

**State collapse**
5. Single run_id with running + succeeded → collapsed state = succeeded
6. Single run_id with running only → collapsed state = running (crash-recovery)
7. Multiple interleaved run_ids collapse correctly by run_id
8. `current_state(component="prediction")` filters correctly
9. `current_state(status="running")` filters correctly

**API behaviour**
10. `open_run` returns a new run_id each call (uuid4 format)
11. `close_run` appends row with matching run_id and terminal status
12. `close_run(run_id, "rate_limited")` accepted as a valid terminal status
13. `refresh_index` writes file with 4 section headers + current timestamp
14. `refresh_index` uses atomic tmp+rename (no `.tmp.*` artifacts left)

**End-to-end**
15. `open_run` → `refresh_index` → Run Index.md "In Flight" section shows the running row; then `close_run` → `refresh_index` → same run now appears in the per-component section, no longer In Flight

---

## 12. Implementation Order (TDD)

1. Write plan file (this document) ✓
2. Create empty `earnings-analysis/operations/` dir + seeded empty `run_ledger.jsonl`
3. Create `scripts/earnings/run_ledger.py` with full API but `pass`-body stubs
4. Write `scripts/earnings/test_run_ledger.py` with all 15 tests (they fail)
5. Implement `append`, `read_all`, `current_state` → primitive tests green
6. Implement `open_run`, `close_run` → API tests green
7. Implement `refresh_index` → rendering test green
8. Full suite green
9. Wire prediction call site in `earnings_orchestrator.py`
10. Wire learner call site in `earnings_orchestrator.py`
11. Wire guidance call site in `scripts/extraction_worker.py` (include rate_limited branch)
12. Seed `Run Index.md` with header + empty sections (auto-regenerates on first run)
13. Re-run full regression suite across all obsidian-capture + earnings tests — must stay at current pass count + 15 new
14. Commit + push

---

## 13. What Is NOT In v1

- ❌ Per-run Markdown mirror notes under `operations/runs/{run_id}.md`
- ❌ Dataview query blocks in Run Index.md (uses static tables instead)
- ❌ `run_id` in `result.md` / `thinking.md` frontmatter
- ❌ Year-rotation of the ledger file (single file for v1; rotate when > 50 MB)
- ❌ ULID run_ids (uuid4 is fine; ULID is a nice-to-have)
- ❌ Any changes to legacy `predictions.csv` / `prediction_processed.csv` (deprecate later)
- ❌ Debounced index refresh (synchronous after each transition is fine at v1 scale)
- ❌ Cross-host coordination (hostPath mount + single-host guarantee is sufficient for current deployment)
- ❌ Elasticsearch / Loki / external log aggregator integration (the JSONL IS the log; ship logs to any aggregator via filebeat later if desired)

---

## 14. Rollback Plan

Revert commit. The ledger file and index note are append-only/regenerable — deleting them is harmless. Orchestrator + extraction_worker lose the wrapping calls and return to their prior behaviour. Zero schema impact anywhere else in the repo.

---

## 15. Future Work (Explicitly Out of Scope)

- Year rotation when ledger > 50 MB
- CLI tool: `python -m run_ledger status` to print current state without opening Obsidian
- Alerting on `rate_limited` storms or consecutive `failed` runs
- Deprecation of `predictions.csv` / `prediction_processed.csv` (after 90 days of ledger being live)
- Per-run Markdown mirror notes if Obsidian browsing UX demands them
- Dataview query block embedded in Run Index.md as optional bonus view (renders only with plugin)
- ULID run_ids for chronological sorting by id

---

## Final Verdict

Architecture is tight. All review-round blockers and trims addressed. Ready to ship.
