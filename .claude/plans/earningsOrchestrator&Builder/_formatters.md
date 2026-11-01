# Move `_fmt_financial_cell` → `_formatters.py` (DAG-flatten + canonical-source cleanup)

**Status:** ready for execution
**Goal:** flatten the renderer DAG by relocating `_fmt_financial_cell` from `renderer/financials.py` to `renderer/_formatters.py` (its natural home — it's a generic formatter alongside `_fmt_num`, `_fmt_money`, `_fmt_pct`).
**Workflow:** dedicated worktree on branch `formatters-cleanup`, 4 commits there, then ff-merge to `main`. Same pattern as the renderer extraction. **Why a worktree?** `extraction-worker` pod uses `hostPath: /home/faisal/EventMarketDB` — any file edit on main is potentially live the moment KEDA next scales the pod up. Worktree + ff-merge guarantees production NEVER sees stages 1–3 intermediate states, only the final post-stage-4 state.
**Total commits:** 4 on the worktree, merged in one ff-merge to main
**Risk:** practically zero — staged so that **legacy behavior is preserved at every step** (existing `from earnings_orchestrator import _fmt_financial_cell` callers never break) AND **strong 4-path function-object identity is required from stage 2 onward** (verified by gate). Stage 1 briefly has two function objects with byte-equivalent output (verified by mandatory equivalence test). Stage 2's cutover collapses them via a permanent re-export shim in `financials.py`. See "Safety invariant — stage-aware" in §0.

---

## Context for a fresh bot (zero prior knowledge assumed)

**Skip this section if you already know the EventMarketDB codebase.** Otherwise read it before §1.

### What is this codebase?
- `EventMarketDB` is a financial-events research repo that ingests SEC filings (8-K earnings releases) and runs an LLM pipeline to predict + post-event-attribute stock price moves.
- The orchestrator at `scripts/earnings/earnings_orchestrator.py` is the central pipeline driver. It:
  1. Resolves an 8-K event into a `quarter_info` dict
  2. Assembles a "prediction bundle" (7 builders fanned out in parallel)
  3. **Renders the bundle into markdown text** for the LLM (this is what we're touching)
  4. Invokes a predictor or learner via the Claude Code SDK
  5. Validates + persists the LLM's output and lessons learned

### What is the renderer?
- The "renderer" turns a Python dict (the bundle) into a deterministic markdown document with 10 sections (header, results, guidance, consensus, financials, inter-quarter events, peers, macro, reference, lessons).
- Each section's renderer is a pure function: `dict in → str out`. No I/O, no logging, no decorators.
- On 2026-04-25 the renderer was extracted from `earnings_orchestrator.py` (then 3,670 lines) into a sub-package at `scripts/earnings/renderer/` (12 modules, ~1,300 LOC moved). See `.claude/plans/earnings_orchestrator_migration.md` for the full extraction record.

### What is `_fmt_financial_cell` and why are we moving it?
- It's a 17-line function that formats a single number for display in a markdown table cell. Signature: `_fmt_financial_cell(value, fmt_type: str) -> str`.
- `fmt_type` ∈ `{"money", "usd", "pct", "count", "ratio"}`. Returns `"—"` for `None` / `NaN` / `±Inf`. Returns `"$1.23"` for usd, `"45.5%"` for pct, `"1.5B"` for big money values, etc.
- It currently lives in `renderer/financials.py` for historical reasons (it was first introduced for `_render_prior_financials`).
- But it's a **generic formatter** — same shape as `_fmt_num` / `_fmt_money` / `_fmt_pct` which all live in `renderer/_formatters.py`.
- `renderer/consensus.py` ALSO uses it (for EPS estimate/actual cells). This creates a `consensus → financials` edge in the renderer's import DAG that doesn't reflect any real conceptual dependency. Moving the function to `_formatters.py` (where it belongs) severs that edge.

### What does "function-object identity" mean and why does it matter?
- In Python, `def foo(): ...` creates a function OBJECT. `import` binds NAMES to existing objects.
- After this move, FOUR import paths exist for `_fmt_financial_cell`. ALL must resolve to the SAME object (verified by Python's `is` operator). If they diverge, calls via different paths could behave differently — a subtle correctness bug.
- The plan's gates (especially the test in stage 4) assert this identity invariant rigorously.

### What is "the 166 tests"?
- Six pytest test files at `scripts/earnings/test_renderer_*.py`, totaling 166 tests baseline:
  | File | Tests | What it asserts |
  |---|---|---|
  | `test_renderer_golden_full.py` | 8 | Full-bundle byte-equality + sha256 vs goldens for 4 saved fixtures |
  | `test_renderer_golden_sections.py` | 40 | Per-section byte-equality (10 sections × 4 fixtures) |
  | `test_renderer_degraded.py` | 13 | Synthetic edge-case bundles (placeholder paths, edge formatters) |
  | `test_renderer_helpers.py` | 63 | Per-helper unit tests (None/NaN/Inf guards, etc.) |
  | `test_renderer_imports.py` | 38 | SHIM_TABLE identity checks (37 symbols × 1 + 1 surface check) |
  | `test_renderer_new_path.py` | 4 | New-path render via `from scripts.earnings.renderer import render_bundle_text` |
- These collectively guard renderer behavior + import contract. If any fail at any stage, the stage is reverted.

### What is the production deploy mechanism?
- `extraction-worker` is a K8s pod in the `processing` namespace. It scales 0→7 replicas via KEDA based on the `extract:pipeline` Redis queue depth.
- The pod's filesystem is a `hostPath` mount of `/home/faisal/EventMarketDB`. So when the pod boots, it loads `earnings_orchestrator.py` directly from the host disk — there's NO Docker image rebuild step.
- **Practical implication:** any commit on `main` becomes "live" the moment the next pod boots. This is why we use a worktree for staging — production never sees intermediate stages.

### Tools assumed
- `bash` ≥ 4 (we use `! grep -q ...`, `<<-EOF` heredocs)
- `git` ≥ 2.5 (for `git worktree`)
- Python venv at `/home/faisal/EventMarketDB/venv/bin/python` (Python 3.11.x with project deps installed). DO NOT use system `python` — it lacks dependencies like `dotenv`, `neo4j`, `claude_agent_sdk`.
- `pytest` is bundled with the venv (no separate install needed)
- The `Edit` / `Write` / `Bash` tools or equivalent for file modification

### ⚠ Tool-call hygiene — MUST READ before stage 1

**Claude Code spawns a fresh shell per `Bash` tool call.** Shell state — `cd` results, `export VAR=...`, `pushd` stacks — does NOT persist across calls. This means:

- The pre-flight block does `cd "$WORKTREE"` and `export REPO=...`, but **those die at the end of that one Bash call**. Subsequent Bash calls start back at whatever cwd Claude Code defaults to (typically `/home/faisal/EventMarketDB` — the MAIN repo, NOT the worktree).
- If you forget this, you'll accidentally edit / test / commit on `main` instead of the worktree, and production sees stages 1–3 — defeating the entire worktree isolation.

**Discipline (mandatory for every tool call from §1.7 onward):**

1. **Bash:** every command starts with `cd /home/faisal/em-formatters-cleanup && ...`, or every multi-line Bash block starts with `cd /home/faisal/em-formatters-cleanup` as its first effective command. Use the literal path; don't rely on `$WORKTREE` or `$REPO` carrying over.
2. **Edit / Write:** every `file_path` parameter uses the absolute worktree path:
   - ✓ `/home/faisal/em-formatters-cleanup/scripts/earnings/renderer/financials.py`
   - ✗ `scripts/earnings/renderer/financials.py` (repo-relative — Edit interprets relative to its own cwd, NOT the prior Bash cwd)
   - ✗ `/home/faisal/EventMarketDB/scripts/earnings/renderer/financials.py` (this is MAIN — would defeat worktree isolation)
3. **Python executable:** the venv lives in main (`/home/faisal/EventMarketDB/venv/bin/python`). That absolute path stays the same regardless of which checkout you're operating on — only source code is in the worktree. Stage blocks either use that full path directly or define `PY=/home/faisal/EventMarketDB/venv/bin/python` inside the same Bash block.

**Safety check after each stage** (before committing):
```bash
cd /home/faisal/EventMarketDB && git status -s scripts/earnings/renderer/ scripts/earnings/test_renderer_*.py scripts/earnings/earnings_orchestrator.py
# expect: NO output during stages 1–4 (main is unchanged; only the worktree has edits)
```
If this command shows ANY changes in main during stages 1–4, you've accidentally edited the main checkout. STOP, revert those changes (`git checkout -- <files>` in main), and re-run the stage in the worktree using the absolute path.

### Where to look if you need more context (further reading)
- `.claude/plans/earnings_orchestrator_migration.md` — the renderer extraction plan that was executed first; describes the renderer/ package layout in detail
- `.claude/plans/earnings_orchestrator_deep_dive.md` — architecture overview of the orchestrator
- `.claude/plans/earnings_orchestrator_visual.html` — visual deck of the orchestrator (open in a browser)
- `scripts/earnings/renderer/__init__.py` — current public surface of the renderer package
- `scripts/earnings/test_renderer_imports.py` — current SHIM_TABLE (the existing back-compat identity contract)
- `git log --oneline pre-renderer-extract..renderer-extract-complete` — the 23-commit extraction history

---

## 0. For a fresh bot — what this is and why it's safe

### What's being changed
ONE function moves from one file to another. Function body is byte-identical at every step. Every old import path keeps working forever via a backward-compat re-export shim.

### The DAG before
```
consensus.py  ──imports _fmt_financial_cell──>  financials.py  ──imports _fmt_*──>  _formatters.py
peers.py      ──imports _iq_*──>  inter_quarter.py
macro.py      ──imports _iq_*──>  inter_quarter.py
financials.py ──imports _fmt_*──>  _formatters.py
guidance.py   ──imports _fmt_*──>  _formatters.py
```

### The DAG after
```
consensus.py  ──imports _fmt_*──>  _formatters.py     (NEW: cross-section edge GONE)
peers.py      ──imports _iq_*──>  inter_quarter.py
macro.py      ──imports _iq_*──>  inter_quarter.py
financials.py ──imports _fmt_*──>  _formatters.py     (now also re-exports _fmt_financial_cell for back-compat)
guidance.py   ──imports _fmt_*──>  _formatters.py
```

The `consensus → financials` edge is severed. `_formatters.py` is the canonical home for ALL generic formatters. `financials.py` retains a re-export shim so that `from scripts.earnings.renderer.financials import _fmt_financial_cell` continues to work for any unaudited caller (forever).

### The safety invariant — stage-aware

The invariant changes shape after stage 2's cutover. A fresh bot must NOT think stage 1 violates the contract just because two function objects briefly coexist.

**Stages 0–1** (pre-cutover): the existing legacy contract holds.
- One function object at `financials._fmt_financial_cell` (the original definition).
- Another, separate function object at `_formatters._fmt_financial_cell` (the verbatim copy added in stage 1).
- The legacy SHIM_TABLE row in `test_renderer_imports.py` still passes because `earnings_orchestrator._fmt_financial_cell` (via the orchestrator's `from renderer.financials import` shim) IS `financials._fmt_financial_cell` — both resolve to the original def.
- The TWO function objects produce IDENTICAL output (verified by stage 1's mandatory equivalence test) but are NOT the same object. Identity by `is` is intentionally NOT required at this stage.

**Stages 2 onward** (post-cutover): the strong 4-path identity contract applies.
**`_fmt_financial_cell` must be exactly ONE function object** reachable from FOUR paths, all returning the same object via Python's `is` operator:
1. `from earnings_orchestrator import _fmt_financial_cell` (legacy top-level)
2. `from scripts.earnings.renderer import _fmt_financial_cell` (package public surface)
3. `from scripts.earnings.renderer.financials import _fmt_financial_cell` (back-compat re-export)
4. `from scripts.earnings.renderer._formatters import _fmt_financial_cell` (canonical home)

If stage 2's cutover or any later stage breaks this strong invariant, the gate fails and the stage is reverted.

### Why this plan is the corrected version
An earlier draft was overly conservative — it left `__init__.py` and the orchestrator shim sourcing from `financials.py` for "minimum diff" reasons. That created a mixed state where the canonical home (`_formatters.py`) and the canonical re-exports disagreed. This corrected plan updates ALL canonical re-exports to source from `_formatters.py`. Identity is preserved, byte-equality is preserved, and the design is now coherent.

---

## 1. Pre-flight verification (run before stage 1; expect all to pass)

```bash
set -eo pipefail
MAIN_REPO=/home/faisal/EventMarketDB
PY=/home/faisal/EventMarketDB/venv/bin/python
cd "$MAIN_REPO"

# 1.1 — confirm main is in expected state
git branch --show-current   # expect: main
git status -s | head        # informational; uncommitted changes are OK if unrelated

# 1.2 — confirm renderer extraction has already landed
test -f scripts/earnings/renderer/__init__.py
test -f scripts/earnings/renderer/_formatters.py
test -f scripts/earnings/renderer/financials.py
test -f scripts/earnings/renderer/consensus.py
echo "renderer/ exists — extraction is in place"

# 1.3 — confirm _fmt_financial_cell is currently in financials.py only
grep -n "^def _fmt_financial_cell" scripts/earnings/renderer/financials.py
# expect: a single line like "53:def _fmt_financial_cell(value, fmt_type: str) -> str:"
test "$(grep -c "^def _fmt_financial_cell" scripts/earnings/renderer/_formatters.py)" = "0"

# 1.4 — confirm consensus.py currently imports from financials
grep -q "from .financials import _fmt_financial_cell" scripts/earnings/renderer/consensus.py
echo "consensus.py imports _fmt_financial_cell from .financials — confirmed"

# 1.5 — confirm import math is currently in financials.py
grep -q "^import math$" scripts/earnings/renderer/financials.py
echo "import math present in financials.py — confirmed (line 9)"

# 1.6 — baseline: all 6 renderer test files green (166 tests)
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_renderer_*.py -q
# expect: 166 passed (162 + 4 new-path); 0 failed

# 1.7 — confirm the target worktree path and branch DON'T already exist.
# A fresh bot must not assume a clean slate — a previous failed attempt may
# have left either behind. If either exists, STOP and clean up first
# (instructions printed below); do not blindly proceed.
WORKTREE=/home/faisal/em-formatters-cleanup
if [ -d "$WORKTREE" ]; then
  echo "FATAL: worktree directory $WORKTREE already exists."
  echo "  To remove: cd $MAIN_REPO && git worktree remove --force $WORKTREE"
  echo "  Then re-run pre-flight from §1.1."
  exit 1
fi
if git show-ref --verify --quiet refs/heads/formatters-cleanup; then
  echo "FATAL: branch 'formatters-cleanup' already exists in this repo."
  echo "  To delete: cd $MAIN_REPO && git branch -D formatters-cleanup"
  echo "  (use -D, not -d, in case the prior branch had unmerged commits)"
  echo "  Then re-run pre-flight from §1.1."
  exit 1
fi
echo "no pre-existing worktree or branch — clean slate confirmed"

# 1.8 — confirm the 7 target files are CLEAN on main. Main may have unrelated
# uncommitted changes (it currently has ~166 untracked test stubs etc.) and
# that's fine, but the files this plan will edit MUST be uncommitted-free,
# otherwise the worktree gets HEAD versions while main has stale state, and
# the eventual ff-merge could surface unexpected conflicts.
TARGETS=(
  "scripts/earnings/renderer/_formatters.py"
  "scripts/earnings/renderer/financials.py"
  "scripts/earnings/renderer/consensus.py"
  "scripts/earnings/renderer/__init__.py"
  "scripts/earnings/earnings_orchestrator.py"
  "scripts/earnings/test_renderer_imports.py"
  "scripts/earnings/test_renderer_helpers.py"
)
DIRTY=()
for f in "${TARGETS[@]}"; do
  if ! git diff --quiet HEAD -- "$f"; then DIRTY+=("$f"); fi
  if ! git diff --cached --quiet HEAD -- "$f"; then DIRTY+=("$f"); fi
done
if [ ${#DIRTY[@]} -gt 0 ]; then
  echo "FATAL: the following target files have uncommitted changes on main:"
  printf '  %s\n' "${DIRTY[@]}"
  echo "  Commit, stash, or restore them before proceeding."
  exit 1
fi
echo "all 7 target files are clean on main — safe to create worktree"

# 1.9 — create the worktree on a fresh branch off main
git worktree add "$WORKTREE" -b formatters-cleanup main
cd "$WORKTREE"
echo "now in worktree at $(pwd) on branch $(git branch --show-current)"

echo "Subsequent stage commands MUST use /home/faisal/em-formatters-cleanup explicitly."
echo "Do not rely on this shell's cd/export state after this Bash call exits."
```

If any pre-flight check fails, stop and investigate before starting stage 1. Once the worktree is created, ALL stage edits and gates run inside `/home/faisal/em-formatters-cleanup`.

---

## 2. Stage 1 — Add `_fmt_financial_cell` to `_formatters.py` + mandatory equivalence test

### What changes (2 files)
1. `scripts/earnings/renderer/_formatters.py` — append the function definition (verbatim copy from financials.py)
2. `scripts/earnings/test_renderer_helpers.py` — append a TEMPORARY equivalence test that asserts both copies produce identical output across all supported `fmt_type` values

### Why this is safe
After stage 1, TWO function definitions exist (one in each file) with byte-identical bodies. Nothing currently imports the new copy in `_formatters.py`, so all existing behavior is unchanged — every renderer call still uses the original `financials.py` copy. The equivalence test guarantees both copies behave identically before we cut over.

### Stage 1, edit A — append to `scripts/earnings/renderer/_formatters.py`

**Append at end of file** (after `_fmt_pct`):

```python


def _fmt_financial_cell(value, fmt_type: str) -> str:
    """Format a single financial metric cell."""
    if value is None:
        return "—"
    v = float(value)
    if not math.isfinite(v):
        return "—"
    if fmt_type == "money":
        return _fmt_money(v)
    if fmt_type == "usd":
        sign = "-" if v < 0 else ""
        return f"{sign}${abs(v):.2f}"
    if fmt_type == "pct":
        return f"{v:.1f}%"
    if fmt_type == "count":
        return _fmt_num(v)
    if fmt_type == "ratio":
        return f"{v:.2f}"
    return str(value)
```

**Verify after the edit:**
```bash
cd /home/faisal/em-formatters-cleanup
grep -c "^def _fmt_financial_cell" scripts/earnings/renderer/_formatters.py    # expect: 1
grep -c "^def _fmt_financial_cell" scripts/earnings/renderer/financials.py     # expect: 1 (unchanged)
/home/faisal/EventMarketDB/venv/bin/python -m py_compile scripts/earnings/renderer/_formatters.py && echo "compile OK"
```

### Stage 1, edit B — append to `scripts/earnings/test_renderer_helpers.py`

**Append at end of file** (after the existing `test_guidance_target_label_unspecified_fallback` test):

```python


# ── TEMPORARY (removed in stage 2) — equivalence between two copies ──
# During stage 1, _fmt_financial_cell exists in BOTH financials.py and
# _formatters.py. This test asserts they produce identical output for every
# supported fmt_type before stage 2's cutover collapses them into ONE object.
# Removed in stage 2 because the cutover makes them the same object (identity
# becomes the stronger guarantee than functional equivalence).

import importlib

def test_TEMP_fmt_financial_cell_equivalence_both_copies():
    """STAGE-1 ONLY: assert financials._fmt_financial_cell and
    _formatters._fmt_financial_cell produce identical output for every
    supported fmt_type and edge case. REMOVE in stage 2."""
    fin = importlib.import_module("scripts.earnings.renderer.financials")._fmt_financial_cell
    fmt = importlib.import_module("scripts.earnings.renderer._formatters")._fmt_financial_cell
    cases = [
        # (value, fmt_type)
        (None, "money"), (None, "usd"), (None, "pct"), (None, "count"), (None, "ratio"),
        (float("nan"), "money"), (float("inf"), "usd"), (float("-inf"), "pct"),
        (0, "money"), (0, "usd"), (0, "pct"), (0, "count"), (0, "ratio"),
        (1.25, "usd"), (-1.25, "usd"), (1.25, "money"), (-1e9, "money"),
        (45.0, "pct"), (-12.5, "pct"),
        (1e6, "count"), (1e9, "count"),
        (2.5, "ratio"), (-0.75, "ratio"),
        (1.0, "unknown_type"),  # falls through to str(value)
    ]
    for value, fmt_type in cases:
        assert fin(value, fmt_type) == fmt(value, fmt_type), (
            f"divergence at ({value!r}, {fmt_type!r}): "
            f"financials={fin(value, fmt_type)!r}, _formatters={fmt(value, fmt_type)!r}"
        )
```

### Stage 1 verification gate
```bash
cd /home/faisal/em-formatters-cleanup
PYTHONPATH=scripts/earnings /home/faisal/EventMarketDB/venv/bin/python -m pytest scripts/earnings/test_renderer_*.py -q
# expect: 167 passed (162 + 4 new-path + 1 new TEMP equivalence test)
PYTHONPATH=scripts/earnings /home/faisal/EventMarketDB/venv/bin/python scripts/earnings/earnings_orchestrator.py --test
# expect: "9 passed, 0 failed out of 9"
```

### Stage 1 commit
```bash
cd /home/faisal/em-formatters-cleanup
git add scripts/earnings/renderer/_formatters.py scripts/earnings/test_renderer_helpers.py
git status -s | head
git commit -m "refactor(renderer): add _fmt_financial_cell to _formatters.py + temp equivalence test (stage 1/4)

Phase 1 of moving _fmt_financial_cell out of financials.py to its natural
home in _formatters.py (it's a generic formatter, not financial-specific).

This stage is purely additive:
  - Copy the function VERBATIM from financials.py to _formatters.py
  - financials.py is UNCHANGED — original definition remains
  - Add a temporary pytest function that asserts the two copies produce
    identical output across all supported fmt_type values + edge cases
    (None, NaN, +/-Inf, 0, big/small numbers, signed values, unknown types)

Two function objects coexist briefly. Stage 2 will collapse them via a
re-export shim in financials.py. The temp test will be removed in stage 2.

All renderer tests still pass: 167 (162 + 4 new-path + 1 TEMP)."
```

### Stage 1 rollback
```bash
cd /home/faisal/em-formatters-cleanup
git revert HEAD
```

---

## 3. Stage 2 — Convert `financials.py` def to re-export shim + remove unused `math` import + drop temp test

### What changes (2 files)
1. `scripts/earnings/renderer/financials.py` — replace `def _fmt_financial_cell(...)` block with `from ._formatters import _fmt_financial_cell` (re-export shim) AND remove the now-unused `import math` line
2. `scripts/earnings/test_renderer_helpers.py` — remove the TEMP equivalence test added in stage 1

### Why this is safe
After stage 2, ONE function object exists in `_formatters.py`. `financials.py` re-exports it via `from ._formatters import _fmt_financial_cell`, so `financials._fmt_financial_cell IS _formatters._fmt_financial_cell` (same Python object). Every existing import path continues to work. The equivalence test from stage 1 becomes redundant (because identity is now a stronger guarantee than functional equivalence).

After this stage, `import math` is no longer needed in financials.py because the only function that used it (`_fmt_financial_cell`) now lives in `_formatters.py` (which has its own `import math`). Verified by reading the file: `_fmt_split_pct`, `_render_revenue_splits`, `_render_prior_financials` use `float()` only — no `math.*` calls.

### Stage 2, edit A — `scripts/earnings/renderer/financials.py`

**Use the Edit tool** (or equivalent) — TWO edits to this file. Approach: add `_fmt_financial_cell` to the existing top import block (idiomatic — all imports at top), and delete the def block entirely. Also remove the now-unused `import math`.

**Edit 1 — combine: remove `import math` + add `_fmt_financial_cell` to the top import block:**
- `old_string`:
  ```python
  from __future__ import annotations

  import math

  from ._formatters import _md_table, _fmt_num, _fmt_money
  ```
- `new_string`:
  ```python
  from __future__ import annotations

  from ._formatters import (
      _md_table, _fmt_num, _fmt_money,
      # PERMANENT back-compat re-export — _fmt_financial_cell was relocated
      # to _formatters.py (stage 2 of the _fmt_financial_cell move). This
      # preserves `from scripts.earnings.renderer.financials import
      # _fmt_financial_cell` for any unaudited caller. Do not remove.
      _fmt_financial_cell,  # noqa: F401
  )
  ```

**Edit 2 — delete the def block entirely (no inline replacement):**
- `old_string`:
  ```python
  def _fmt_financial_cell(value, fmt_type: str) -> str:
      """Format a single financial metric cell."""
      if value is None:
          return "—"
      v = float(value)
      if not math.isfinite(v):
          return "—"
      if fmt_type == "money":
          return _fmt_money(v)
      if fmt_type == "usd":
          sign = "-" if v < 0 else ""
          return f"{sign}${abs(v):.2f}"
      if fmt_type == "pct":
          return f"{v:.1f}%"
      if fmt_type == "count":
          return _fmt_num(v)
      if fmt_type == "ratio":
          return f"{v:.2f}"
      return str(value)


  ```
- `new_string`: (empty — the def block + its trailing blank lines are deleted; the re-export is now in the top import block per Edit 1)

### Stage 2, edit B — `scripts/earnings/test_renderer_helpers.py`

**Remove the TEMP test** added in stage 1:

- `old_string`:
  ```python
  # ── TEMPORARY (removed in stage 2) — equivalence between two copies ──
  # During stage 1, _fmt_financial_cell exists in BOTH financials.py and
  # _formatters.py. This test asserts they produce identical output for every
  # supported fmt_type before stage 2's cutover collapses them into ONE object.
  # Removed in stage 2 because the cutover makes them the same object (identity
  # becomes the stronger guarantee than functional equivalence).

  import importlib

  def test_TEMP_fmt_financial_cell_equivalence_both_copies():
      """STAGE-1 ONLY: assert financials._fmt_financial_cell and
      _formatters._fmt_financial_cell produce identical output for every
      supported fmt_type and edge case. REMOVE in stage 2."""
      fin = importlib.import_module("scripts.earnings.renderer.financials")._fmt_financial_cell
      fmt = importlib.import_module("scripts.earnings.renderer._formatters")._fmt_financial_cell
      cases = [
          # (value, fmt_type)
          (None, "money"), (None, "usd"), (None, "pct"), (None, "count"), (None, "ratio"),
          (float("nan"), "money"), (float("inf"), "usd"), (float("-inf"), "pct"),
          (0, "money"), (0, "usd"), (0, "pct"), (0, "count"), (0, "ratio"),
          (1.25, "usd"), (-1.25, "usd"), (1.25, "money"), (-1e9, "money"),
          (45.0, "pct"), (-12.5, "pct"),
          (1e6, "count"), (1e9, "count"),
          (2.5, "ratio"), (-0.75, "ratio"),
          (1.0, "unknown_type"),  # falls through to str(value)
      ]
      for value, fmt_type in cases:
          assert fin(value, fmt_type) == fmt(value, fmt_type), (
              f"divergence at ({value!r}, {fmt_type!r}): "
              f"financials={fin(value, fmt_type)!r}, _formatters={fmt(value, fmt_type)!r}"
          )
  ```
- `new_string`: (empty — delete the entire block, leave one trailing newline at EOF)

### Stage 2 verification gate
```bash
cd /home/faisal/em-formatters-cleanup
# Sanity: only ONE definition of _fmt_financial_cell now (positive grep — should match exactly once)
test "$(grep -rn "^def _fmt_financial_cell" scripts/earnings/renderer/ | wc -l)" = "1"
grep -rn "^def _fmt_financial_cell" scripts/earnings/renderer/   # informational

# Sanity: financials.py no longer imports math (negative grep — `! grep -q` survives `set -e`)
! grep -q "^import math" scripts/earnings/renderer/financials.py && echo "import math removed from financials.py — confirmed"

# Compile check
/home/faisal/EventMarketDB/venv/bin/python -m py_compile scripts/earnings/renderer/financials.py scripts/earnings/renderer/_formatters.py && echo "compile OK"

# Identity check: financials's name now resolves to _formatters's def
PYTHONPATH=. /home/faisal/EventMarketDB/venv/bin/python -c "
from scripts.earnings.renderer import financials, _formatters
assert financials._fmt_financial_cell is _formatters._fmt_financial_cell, 'IDENTITY BROKEN'
print('financials._fmt_financial_cell is _formatters._fmt_financial_cell — PASS')
"

# Full renderer suite
PYTHONPATH=scripts/earnings /home/faisal/EventMarketDB/venv/bin/python -m pytest scripts/earnings/test_renderer_*.py -q
# expect: 166 passed (back to baseline + 4 new-path; the TEMP test is gone)

# Inline --test
PYTHONPATH=scripts/earnings /home/faisal/EventMarketDB/venv/bin/python scripts/earnings/earnings_orchestrator.py --test
# expect: "9 passed, 0 failed out of 9"
```

### Stage 2 commit
```bash
cd /home/faisal/em-formatters-cleanup
git add scripts/earnings/renderer/financials.py scripts/earnings/test_renderer_helpers.py
git status -s | head
git commit -m "refactor(renderer): convert financials._fmt_financial_cell to re-export shim + drop unused math import + remove temp test (stage 2/4)

Stage 2 of moving _fmt_financial_cell to _formatters.py. After this stage
ONE function object exists, reachable from BOTH paths via the re-export.

  - financials.py: replace local def with 'from ._formatters import
    _fmt_financial_cell' (PERMANENT re-export — preserves the
    from scripts.earnings.renderer.financials import path forever)
  - financials.py: remove 'import math' (no longer needed — _fmt_split_pct,
    _render_revenue_splits, _render_prior_financials don't use math.*)
  - test_renderer_helpers.py: drop the temp equivalence test added in
    stage 1 (now redundant — identity is a stronger guarantee than
    functional equivalence)

Identity invariant verified post-cutover:
  financials._fmt_financial_cell is _formatters._fmt_financial_cell

All renderer tests still pass: 166 (162 + 4 new-path; -1 TEMP)."
```

### Stage 2 rollback
```bash
cd /home/faisal/em-formatters-cleanup
git revert HEAD
```

---

## 4. Stage 3 — Update canonical imports (consensus.py + renderer/__init__.py + orchestrator shim)

### What changes (3 files)
1. `scripts/earnings/renderer/consensus.py` — import `_fmt_financial_cell` from `._formatters` instead of `.financials` (DAG flatten — primary goal)
2. `scripts/earnings/renderer/__init__.py` — re-export `_fmt_financial_cell` from `._formatters` instead of `.financials` (canonical-source consistency)
3. `scripts/earnings/earnings_orchestrator.py` — in the consolidated shim block, move `_fmt_financial_cell` from the `renderer.financials` import line to the `renderer._formatters` import line (canonical-source consistency)

### Why this is safe
Function-object identity is unchanged at every step (after stage 2, `financials._fmt_financial_cell IS _formatters._fmt_financial_cell`). All three edits source the function via the canonical path now. The `from .financials import _fmt_financial_cell` form continues to work for any external code we don't know about (because financials.py keeps the re-export shim from stage 2).

### Stage 3, edit A — `scripts/earnings/renderer/consensus.py`

**Edit 1 — change the import:**
- `old_string`:
  ```python
  from ._formatters import _md_table, _fmt_money, _fmt_pct
  from .financials import _fmt_financial_cell
  ```
- `new_string`:
  ```python
  from ._formatters import _md_table, _fmt_money, _fmt_pct, _fmt_financial_cell
  ```

**Edit 2 — update the docstring to reflect the cleaner DAG:**
- `old_string`:
  ```python
  """Section 4 — Consensus History (beat/miss + revision momentum).

  Extracted from earnings_orchestrator.py (commit 12/20) — body copied verbatim
  from the pre-renderer-extract baseline at line 656.

  Imports `_fmt_financial_cell` from the sibling `financials` module
  (used at line 697 for EPS estimate/actual cells); `_md_table`, `_fmt_money`,
  `_fmt_pct` from `_formatters`.
  """
  ```
- `new_string`:
  ```python
  """Section 4 — Consensus History (beat/miss + revision momentum).

  Extracted from earnings_orchestrator.py (commit 12/20) — body copied verbatim
  from the pre-renderer-extract baseline at line 656.

  All formatter imports come from `_formatters` (single canonical source).
  """
  ```

### Stage 3, edit B — `scripts/earnings/renderer/__init__.py`

- `old_string`:
  ```python
  from ._formatters import _md_table, _fmt_num, _fmt_money, _fmt_pct
  from .header import _render_header
  from .results import _render_results_and_expectations, _render_reference
  from .guidance import (
      _fmt_guidance_value, _compute_change, _fmt_metric_label,
      _guidance_target_key, _guidance_target_label, _is_segmented_label,
      _render_forward_guidance,
  )
  from .consensus import _render_consensus_history
  from .financials import (
      _fmt_financial_cell, _fmt_split_pct,
      _render_revenue_splits, _render_prior_financials,
  )
  ```
- `new_string`:
  ```python
  from ._formatters import (
      _md_table, _fmt_num, _fmt_money, _fmt_pct,
      _fmt_financial_cell,  # canonical home (financials.py keeps a re-export for back-compat)
  )
  from .header import _render_header
  from .results import _render_results_and_expectations, _render_reference
  from .guidance import (
      _fmt_guidance_value, _compute_change, _fmt_metric_label,
      _guidance_target_key, _guidance_target_label, _is_segmented_label,
      _render_forward_guidance,
  )
  from .consensus import _render_consensus_history
  from .financials import (
      _fmt_split_pct,
      _render_revenue_splits, _render_prior_financials,
  )
  ```

### Stage 3, edit C — `scripts/earnings/earnings_orchestrator.py`

**Edit 1 — add `_fmt_financial_cell` to the `_formatters` import line:**
- `old_string`:
  ```python
  from scripts.earnings.renderer._formatters import (  # noqa: F401
      _md_table, _fmt_num, _fmt_money, _fmt_pct,
  )
  ```
- `new_string`:
  ```python
  from scripts.earnings.renderer._formatters import (  # noqa: F401
      _md_table, _fmt_num, _fmt_money, _fmt_pct,
      _fmt_financial_cell,  # canonical home (financials.py keeps a re-export for back-compat)
  )
  ```

**Edit 2 — remove `_fmt_financial_cell` from the `renderer.financials` import line:**
- `old_string`:
  ```python
  from scripts.earnings.renderer.financials import (  # noqa: F401
      _FINANCIAL_SECTIONS,
      _fmt_financial_cell, _fmt_split_pct,
      _render_revenue_splits, _render_prior_financials,
  )
  ```
- `new_string`:
  ```python
  from scripts.earnings.renderer.financials import (  # noqa: F401
      _FINANCIAL_SECTIONS,
      _fmt_split_pct,
      _render_revenue_splits, _render_prior_financials,
  )
  ```

### Stage 3 verification gate
```bash
cd /home/faisal/em-formatters-cleanup
# DAG check: consensus.py no longer imports from .financials (negative grep)
! grep -q "from .financials" scripts/earnings/renderer/consensus.py && echo "consensus.py → no .financials import — DAG flattened"

# __init__.py canonical source check (informational)
grep -A1 "_fmt_financial_cell" scripts/earnings/renderer/__init__.py | head -4
# expect: appears under _formatters import block, NOT under .financials block

# Orchestrator shim canonical source check (informational)
grep -B1 -A1 "_fmt_financial_cell" scripts/earnings/earnings_orchestrator.py | head -10
# expect: under _formatters import block, NOT under financials block
# (the test_renderer_imports.py SHIM_TABLE entry will still mention financials —
#  that's intentional, it's the legacy-path proof; the new test in stage 4
#  adds the 4-path canonical-identity proof)

# Compile checks
/home/faisal/EventMarketDB/venv/bin/python -m py_compile \
    scripts/earnings/renderer/consensus.py \
    scripts/earnings/renderer/__init__.py \
    scripts/earnings/earnings_orchestrator.py && echo "compile OK"

# Identity check across all 4 paths (NEW — proves canonical cleanup didn't break anything)
PYTHONPATH=. /home/faisal/EventMarketDB/venv/bin/python <<'PY_EOF'
import sys
sys.path.insert(0, "scripts/earnings")
import earnings_orchestrator
import scripts.earnings.renderer
import scripts.earnings.renderer.financials
import scripts.earnings.renderer._formatters

obj_orch = earnings_orchestrator._fmt_financial_cell
obj_pkg  = scripts.earnings.renderer._fmt_financial_cell
obj_fin  = scripts.earnings.renderer.financials._fmt_financial_cell
obj_fmt  = scripts.earnings.renderer._formatters._fmt_financial_cell

assert obj_orch is obj_pkg is obj_fin is obj_fmt, (
    "IDENTITY BROKEN: not all 4 paths resolve to the same object")
print("all 4 paths resolve to the SAME function object — PASS")
PY_EOF

# Full renderer suite
PYTHONPATH=scripts/earnings /home/faisal/EventMarketDB/venv/bin/python -m pytest scripts/earnings/test_renderer_*.py -q
# expect: 166 passed

# Inline --test
PYTHONPATH=scripts/earnings /home/faisal/EventMarketDB/venv/bin/python scripts/earnings/earnings_orchestrator.py --test
# expect: "9 passed, 0 failed out of 9"
```

### Stage 3 commit
```bash
cd /home/faisal/em-formatters-cleanup
git add scripts/earnings/renderer/consensus.py scripts/earnings/renderer/__init__.py scripts/earnings/earnings_orchestrator.py
git status -s | head
git commit -m "refactor(renderer): canonical _fmt_financial_cell imports — _formatters everywhere (stage 3/4)

Updates ALL canonical re-exports of _fmt_financial_cell to source from
_formatters.py (its new canonical home), achieving:

  - consensus.py: imports from ._formatters (no longer from .financials)
    -> cross-section consensus -> financials edge SEVERED — DAG flattened
  - renderer/__init__.py: re-exports from ._formatters (canonical source)
  - earnings_orchestrator.py shim: imports from renderer._formatters
    (moved out of the renderer.financials import block)

financials.py STILL re-exports _fmt_financial_cell from _formatters
(permanent back-compat shim from stage 2 — preserves
  from scripts.earnings.renderer.financials import _fmt_financial_cell
for any unaudited caller).

Identity invariant verified: all 4 paths resolve to the same function object:
  earnings_orchestrator._fmt_financial_cell
  scripts.earnings.renderer._fmt_financial_cell
  scripts.earnings.renderer.financials._fmt_financial_cell
  scripts.earnings.renderer._formatters._fmt_financial_cell

All renderer tests still pass: 166."
```

### Stage 3 rollback
```bash
cd /home/faisal/em-formatters-cleanup
git revert HEAD
```

---

## 5. Stage 4 — Add permanent 4-path identity test

### What changes (1 file)
1. `scripts/earnings/test_renderer_imports.py` — append a NEW test asserting `_fmt_financial_cell` resolves to the same function object across all 4 import paths

**The existing SHIM_TABLE entry** (`("_fmt_financial_cell", "earnings_orchestrator", "scripts.earnings.renderer.financials")`) **stays UNCHANGED** — it continues to prove that the legacy `from scripts.earnings.renderer.financials import` path still works (it does, via the back-compat shim from stage 2).

### Why this is safe
Pure additive — adds one test function. The test asserts an invariant that's already true after stages 2 and 3 (verified by the inline check in stage 3's gate). Promoting this check from a one-shot bash invocation to a pytest function makes it a permanent regression guard.

### Stage 4, edit — `scripts/earnings/test_renderer_imports.py`

**Append at end of file** (after the existing `test_renderer_package_public_surface` function):

```python


def test_fmt_financial_cell_identity_all_four_paths():
    """All four import paths for _fmt_financial_cell resolve to the SAME
    function object. This is the load-bearing invariant of the
    _fmt_financial_cell relocation (see .claude/plans/_formatters.md).

    The 4 paths:
      1. earnings_orchestrator._fmt_financial_cell        (legacy top-level)
      2. scripts.earnings.renderer._fmt_financial_cell    (package public surface, via __init__.py)
      3. scripts.earnings.renderer.financials._fmt_financial_cell  (back-compat re-export)
      4. scripts.earnings.renderer._formatters._fmt_financial_cell (canonical home)

    If this test fails, identity has been broken — likely someone added a
    parallel definition or wrapped the function. Revert immediately and
    investigate; the back-compat contract has been violated.
    """
    obj_orch = importlib.import_module("earnings_orchestrator")._fmt_financial_cell
    obj_pkg  = importlib.import_module("scripts.earnings.renderer")._fmt_financial_cell
    obj_fin  = importlib.import_module("scripts.earnings.renderer.financials")._fmt_financial_cell
    obj_fmt  = importlib.import_module("scripts.earnings.renderer._formatters")._fmt_financial_cell
    assert obj_orch is obj_pkg, "earnings_orchestrator vs renderer package: NOT same object"
    assert obj_orch is obj_fin, "earnings_orchestrator vs renderer.financials: NOT same object"
    assert obj_orch is obj_fmt, "earnings_orchestrator vs renderer._formatters: NOT same object"
```

### Stage 4 verification gate
```bash
cd /home/faisal/em-formatters-cleanup
# Run the new identity test specifically
PYTHONPATH=scripts/earnings /home/faisal/EventMarketDB/venv/bin/python -m pytest \
    scripts/earnings/test_renderer_imports.py::test_fmt_financial_cell_identity_all_four_paths -v
# expect: 1 passed

# Confirm the legacy SHIM_TABLE entry is UNCHANGED (still asserts financials path)
grep "_fmt_financial_cell.*scripts.earnings.renderer.financials" scripts/earnings/test_renderer_imports.py
# expect: a match (the SHIM_TABLE entry)

# Full renderer suite
PYTHONPATH=scripts/earnings /home/faisal/EventMarketDB/venv/bin/python -m pytest scripts/earnings/test_renderer_*.py -q
# expect: 167 passed (166 + 1 new identity test)
```

### Stage 4 commit
```bash
cd /home/faisal/em-formatters-cleanup
git add scripts/earnings/test_renderer_imports.py
git status -s | head
git commit -m "test(renderer): add permanent 4-path identity test for _fmt_financial_cell (stage 4/4)

Promotes the identity invariant verified in stage 3's bash gate to a
permanent pytest regression guard. Asserts that all 4 import paths for
_fmt_financial_cell resolve to the same function object:

  1. earnings_orchestrator._fmt_financial_cell
  2. scripts.earnings.renderer._fmt_financial_cell (via __init__.py)
  3. scripts.earnings.renderer.financials._fmt_financial_cell (back-compat)
  4. scripts.earnings.renderer._formatters._fmt_financial_cell (canonical)

The existing SHIM_TABLE entry mapping orchestrator->renderer.financials is
LEFT UNCHANGED — it continues to prove the legacy path still works via the
back-compat re-export. The new test adds the 'all paths equal' assertion
without weakening the legacy-path proof.

If this test fails: identity has been broken. Likely someone added a
parallel definition or a wrapper function — revert and investigate.

All renderer tests pass: 167 (166 + 1 new identity)."
```

### Stage 4 rollback
```bash
cd /home/faisal/em-formatters-cleanup
git revert HEAD
```

---

## 6. Final state verification (after all 4 stages, run inside the worktree)

```bash
set -eo pipefail
cd /home/faisal/em-formatters-cleanup
PY=/home/faisal/EventMarketDB/venv/bin/python

echo "=== File state ==="
echo "_fmt_financial_cell defs across renderer/ (expect: 1 line, in _formatters.py):"
grep -rn "^def _fmt_financial_cell" scripts/earnings/renderer/
test "$(grep -rn "^def _fmt_financial_cell" scripts/earnings/renderer/ | wc -l)" = "1"

echo ""
echo "consensus.py imports from .financials? (expect: NONE):"
! grep -q "from .financials" scripts/earnings/renderer/consensus.py && echo "  none — DAG flattened"

echo ""
echo "financials.py contains 'import math'? (expect: NONE):"
! grep -q "^import math" scripts/earnings/renderer/financials.py && echo "  none — cleaned up"

echo ""
echo "financials.py re-exports _fmt_financial_cell? (expect: re-export line present):"
grep -q "_fmt_financial_cell" scripts/earnings/renderer/financials.py && echo "  re-export present — back-compat preserved"

echo ""
echo "=== Renderer test suite (no | tail; full output below) ==="
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_renderer_*.py -v --tb=short
# expect: 167 passed (166 baseline + 1 new identity test from stage 4); pytest exit 0

echo ""
echo "=== Inline --test mode ==="
PYTHONPATH=scripts/earnings $PY scripts/earnings/earnings_orchestrator.py --test
# expect: "9 passed, 0 failed out of 9"

echo ""
echo "=== Identity check ==="
PYTHONPATH=. $PY <<'PY_EOF'
import sys
sys.path.insert(0, "scripts/earnings")
import earnings_orchestrator
import scripts.earnings.renderer
import scripts.earnings.renderer.financials
import scripts.earnings.renderer._formatters
ids = {
    "orchestrator":          id(earnings_orchestrator._fmt_financial_cell),
    "renderer (__init__)":   id(scripts.earnings.renderer._fmt_financial_cell),
    "renderer.financials":   id(scripts.earnings.renderer.financials._fmt_financial_cell),
    "renderer._formatters":  id(scripts.earnings.renderer._formatters._fmt_financial_cell),
}
for path, oid in ids.items():
    print(f"  id({path:<25}) = {oid}")
unique = set(ids.values())
assert len(unique) == 1, f"BROKEN: {len(unique)} distinct objects, should be 1"
print("all 4 paths resolve to ONE function object — PASS")
PY_EOF

echo ""
echo "=== Consumer-import smoke ==="
PYTHONPATH=scripts $PY -c "
import scripts.run_ab_baseline
import scripts.run_burl_ab_sequential
import scripts.run_nvda_ab_sequential
import scripts.run_q3_from_existing_bundle
import scripts.run_calibration_sequential
import scripts.calibrate_learner
import scripts.run_phase4_big
print('all 7 consumer scripts import OK')
"

echo ""
echo "=== Commit log on the formatters-cleanup branch ==="
git log --oneline -5
```

Expected outcome: all checks pass, 4 stages reflected in `git log`, identity invariant proven.

### Merge to main + cleanup

Once §6 is fully green inside the worktree, fast-forward main and clean up.

**Important: merge during an idle window.** `git merge --ff-only` updates working-tree files SEQUENTIALLY (file-by-file). If `extraction-worker` boots mid-merge, the pod could load a half-merged orchestrator (e.g., shim block updated but consensus.py not yet). Risk window is milliseconds, but real. Prevent it by checking the `extract:pipeline` Redis queue is empty AND no extraction-worker pod is currently starting:

```bash
# Pre-merge production-quiescence check
cd /home/faisal/EventMarketDB
echo "=== Redis queue depth (extract:pipeline) ==="
kubectl -n infrastructure exec deploy/redis -- redis-cli LLEN extract:pipeline 2>/dev/null || \
  echo "(redis check skipped — exec failed; verify queue manually)"
# expect: 0  (if non-zero, wait or pause KEDA before merging)

echo "=== Currently running/starting extraction-worker pods ==="
kubectl -n processing get pods -l app=extraction-worker --no-headers 2>/dev/null
# expect: NO output (deployment is at 0/0 replicas during idle)

echo "=== KEDA scaler state ==="
kubectl -n processing get scaledobject extraction-worker-scaler --no-headers 2>/dev/null
# informational — confirms KEDA is monitoring the queue
```

If queue is non-empty OR a pod is starting, EITHER:
- Wait for the queue to drain naturally (typical: a few minutes after queue stops growing)
- OR temporarily pause KEDA with the supported pause annotation:
  ```bash
  kubectl -n processing annotate scaledobject extraction-worker-scaler autoscaling.keda.sh/paused-replicas="0" --overwrite
  ```
  After the merge + main gate, unpause by removing the annotation:
  ```bash
  kubectl -n processing annotate scaledobject extraction-worker-scaler autoscaling.keda.sh/paused-replicas-
  ```
  Do **not** patch `maxReplicaCount: 0`; the live scaler uses the pause annotation path, and `maxReplicaCount: 0` is not the intended KEDA control surface here.

Once production is quiescent, do the merge:

```bash
cd /home/faisal/EventMarketDB
PY=/home/faisal/EventMarketDB/venv/bin/python
git fetch . formatters-cleanup    # update local refs (no-op for the worktree branch but harmless)
git merge --ff-only formatters-cleanup
echo "main HEAD now at: $(git rev-parse HEAD | head -c 8)"

# Re-run gate on main (sanity — should produce identical results)
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_renderer_*.py -q
# expect: 167 passed (166 baseline + 1 stage-4 identity test)

# Re-confirm post-merge production state
kubectl -n processing get pods -l app=extraction-worker --no-headers 2>/dev/null
# informational — KEDA may have scaled up if queue items arrived
# If a pod IS running now, it's loading the FINAL post-merge state (safe)

# Clean up worktree + branch
git worktree remove /home/faisal/em-formatters-cleanup
git branch -d formatters-cleanup
```

Optionally push to origin:
```bash
cd /home/faisal/EventMarketDB
git push origin main
```

---

## 7. What we are explicitly NOT doing (and why)

These were considered and deliberately excluded:

1. **Removing `financials.py`'s re-export shim.** The shim costs 1 line and is permanent. Removing it would risk breaking any unaudited caller doing `from scripts.earnings.renderer.financials import _fmt_financial_cell`. There's no functional benefit to dropping it.

2. **Renaming the SHIM_TABLE entry from `financials` to `_formatters`.** The existing entry proves the legacy path works. Changing it would weaken the test. Stage 4 ADDS a new test (the 4-path identity check) without modifying the existing entry.

3. **Moving any other function to `_formatters.py`.** `_fmt_split_pct` could arguably be a generic formatter too, but it's currently only used in financials and moving it has no DAG benefit. Out of scope.

4. **Refactoring the function body or call sites.** Pure relocation — the function is byte-identical at every stage. No behavior change.

5. **Updating documentation files** (deep-dive, visual.html, migration.md). They reference `_fmt_financial_cell` only at the conceptual level; relocation doesn't invalidate any prose. Docs can be touched in a follow-up if/when desired.

---

## 8. Aggregate risk assessment

| Stage | Files touched | Function objects | Identity preserved? | Goldens pass? | Reversibility |
|---|---|---|---|---|---|
| 1 (copy + temp test) | 2 | 2 (briefly) | Existing SHIM_TABLE check still passes (orchestrator → financials → orig def) | yes | `git revert` |
| 2 (cutover + math removal + drop temp) | 2 | 1 (collapsed via re-export) | yes (financials → _formatters) | yes | `git revert` |
| 3 (canonical imports) | 3 | 1 | yes (all paths → _formatters) | yes | `git revert` |
| 4 (identity test) | 1 | 1 | yes (now permanently asserted) | yes | `git revert` |

**Aggregate residual risk: ~0%** because:
- Function body is byte-identical across all stages
- Identity is preserved across all 4 paths from stage 2 onward
- All 6 renderer test files (166 tests baseline; 167 during stages 1 + after stage 4) pass at every stage
- The back-compat re-export in financials.py guarantees zero break for any unaudited caller
- Each stage is independently revertible with `git revert HEAD`
- Worktree workflow ensures production NEVER sees stages 1–3 intermediate states; only the final post-stage-4 state lands on main via ff-merge

---

## 9. Done criteria

- [ ] Pre-flight: worktree `/home/faisal/em-formatters-cleanup` exists on branch `formatters-cleanup` (off main); 166 baseline tests green
- [ ] Stage 1 commit: equivalence test passes, 167 tests green (166 baseline + 1 TEMP)
- [ ] Stage 2 commit: identity check passes, 166 tests green (TEMP removed), `import math` gone from financials.py
- [ ] Stage 3 commit: `from .financials` gone from consensus.py, all 4 paths identity-equal, 166 tests green
- [ ] Stage 4 commit: new identity test passes, 167 tests green (166 + 1 new identity test)
- [ ] Final verification (§6) all green inside the worktree
- [ ] `git log --oneline` on the worktree branch shows 4 sequential commits — three `refactor(renderer):` + one `test(renderer):`
- [ ] FF-merge into main, re-run gate on main, identical results
- [ ] Cleanup: worktree removed, `formatters-cleanup` branch deleted
- [ ] Optionally push to origin: `git push origin main`

---

## 10. Common pitfalls + edge cases (project-specific)

A fresh bot may hit these without warning. Each item explains how to recognize and fix it.

### 10.1 Pre-existing test_fmt_guards.py crashes pytest collection
`scripts/earnings/test_fmt_guards.py` is a script-style test that calls `sys.exit()` at module top-level. It crashes pytest's COLLECTOR when `pytest scripts/earnings/` is invoked without an `--ignore`. This is a **pre-existing repo bug**, not caused by our work.

**Recognize:** `INTERNALERROR> SystemExit: 0` during collection.
**Fix:** the per-stage gates in this plan target `test_renderer_*.py` specifically (not all of `scripts/earnings/`), so this issue doesn't apply. If you ever expand the gate, use `--ignore=scripts/earnings/test_fmt_guards.py`.

### 10.2 The line numbers in this plan are illustrative
The pre-flight says `_fmt_financial_cell` is at "line 53" of financials.py and `import math` is at "line 9". These ARE accurate at the time of writing, but Python files shift. The Edit operations in stages 1–4 use `old_string` / `new_string` semantic matching, NOT line numbers — they will work regardless of line-number drift. Trust the semantic match; the line numbers are just orientation hints.

### 10.3 If `import importlib` is missing in test_renderer_helpers.py
Stage 1 adds `import importlib` inside the temp test block. `test_renderer_helpers.py` doesn't otherwise use `importlib`, so the import lives in the temp block. Stage 2's deletion of the temp block REMOVES that import too — that's intentional and correct.

`test_renderer_imports.py` (where stage 4 adds the new identity test) already has `import importlib` at the top — stage 4 doesn't need to add a new import line.

### 10.4 If the Python venv is missing
Plan assumes `/home/faisal/EventMarketDB/venv/bin/python` exists with project deps. **Do not** fall back to system `python`/`python3` — they lack `dotenv`, `neo4j`, `claude_agent_sdk`, etc. and the orchestrator's import will fail at the top.

**Recognize:** `ModuleNotFoundError: No module named 'dotenv'` (or similar) when running any gate.
**Fix:** verify `ls /home/faisal/EventMarketDB/venv/bin/python` returns the binary. If absent, STOP and ask — recreating the venv is out of scope for this plan.

### 10.5 If `git worktree add` fails because the worktree path already exists
This is the failure mode pre-flight §1.7 catches. Fresh bot should NOT proceed past the `FATAL` message — instead, run the cleanup commands printed by §1.7 and re-run pre-flight from §1.1. Do NOT use `--force` to overwrite — it could discard work from a prior partial attempt.

### 10.6 If a stage's gate fails
Per the plan: **never proceed past a red gate**. The procedure for each red gate:
1. Look at the failing assertion message — it usually identifies the file + line + expected vs actual
2. If the cause is obvious (typo, missed Edit), fix in place and re-run the gate
3. If the cause is non-obvious, run `git revert HEAD` to undo the stage's commit (keeps history bisect-friendly), then diagnose from a known-good state
4. Never amend or `git reset --hard` the previous commit — that destroys the bisect property and could lose the gate's audit trail

### 10.7 If stage 2's `from ._formatters import _fmt_financial_cell` line doesn't resolve
This happens if stage 1 was forgotten or reverted. Stage 2 depends on stage 1 having added the function to `_formatters.py`. **Recognize:** `ImportError: cannot import name '_fmt_financial_cell' from 'scripts.earnings.renderer._formatters'` during gate.
**Fix:** verify with `grep -c "^def _fmt_financial_cell" scripts/earnings/renderer/_formatters.py` — it should return `1`. If `0`, redo stage 1 first.

### 10.8 If extraction-worker scales up mid-execution
The `extraction-worker` pod loads `earnings_orchestrator.py` from disk on boot. If it boots between stages (in the worktree), no production impact (worktree is isolated from the hostPath mount — main is mounted, not the worktree). **The risk window is the §6 ff-merge** — addressed by the production-quiescence check in §6 above.

If the merge happens during a queue burst (you forgot the quiescence check), production might briefly load a partially-merged state. Recovery: `git revert HEAD` on main + push, queue will drain, restart workers via `kubectl -n processing rollout restart deploy/extraction-worker` (forces a clean reload from the now-reverted disk state).

### 10.9 If you need to abort mid-execution
At any point before §6 merge:
- `cd /home/faisal/EventMarketDB && git worktree remove --force /home/faisal/em-formatters-cleanup`
- `git branch -D formatters-cleanup`
- Main is untouched; production sees nothing.

After §6 merge but before push:
- `cd /home/faisal/EventMarketDB && git reset --hard HEAD~1` (rewinds the merge — only safe before `git push`)
- Production extraction-worker would need a manual restart to reload pre-merge code: `kubectl -n processing rollout restart deploy/extraction-worker` (or wait for KEDA to scale 0 then back up)

After push to origin:
- Revert via `git revert <merge-commit>` + push. Don't force-push.

---

**End of plan.**
