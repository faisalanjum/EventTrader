# warmup_cache Domain Split — Zero-Regression Function-Extraction Plan

**Status:** PLANNING ONLY. No implementation has been done from this plan yet.
**Date prepared:** 2026-04-26
**Branch:** `warmup-cache-domain-split`
**Worktree:** `/home/faisal/em-warmup-cache-split`
**Total commits: 10 required** (Stage 0 = 1, Stages 1–3 each = 2, Stage 4 = 1, Stage 5 = 1, Stage 6 README = 1).
**Aggregate risk: practically zero** if every stage gate is run and green before the next commit lands.

**Primary goal:** split the three domain builders (`build_8k_packet`, `build_guidance_history`, `build_inter_quarter_context`) plus their helpers + queries out of the 2,066-line `scripts/earnings/builders/warmup_cache.py` into three focused canonical domain modules, while keeping `warmup_cache.py` as a permanent facade that re-exports every relocated symbol so that EXTERNAL callers — bare imports, the `.claude/skills` shim, `warmup_cache.sh`, the orchestrator, the existing test suite, the prediction-context debug one-liners, and skill markdown — all keep working unchanged. The ONE intentional internal-caller import rewrite is Stage 4's `adapters.py` lazy-import canonicalization (REQUIRED — 3 lazy imports rerouted from the warmup_cache facade hop to the canonical domain modules; identity is preserved either way).

**Non-negotiable safety rule:** every existing import path of every relocated symbol MUST still resolve via Python `is` to the SAME function object after every stage and after merge. No EXTERNAL callers update imports. No external call sites rewrite. The facade re-export is the load-bearing contract — Stage 4's adapter update is the sole intentional internal-caller change and explicitly preserves identity (both `wc.X` and `domain_module.X` still return the SAME object).

This plan inflates a prior 236-line outline (which previously occupied this same file path) into a per-commit-staged execution plan with edit instructions, gates, rollback templates, and contract tests ready for a zero-context executor. Module names and helper-distribution map are inherited from that outline; everything else is new.

---

## 0. Tool-Call Hygiene (READ FIRST — applies to every stage)

The executing bot lives in a fresh shell per `Bash` call. State does NOT carry across calls.

- `cd` does not persist. Every `Bash` call MUST start with `cd /home/faisal/em-warmup-cache-split && ...` once the worktree exists; before then, `cd /home/faisal/EventMarketDB && ...`. Or use absolute paths exclusively.
- `export VAR=...` does not carry. Set `PYTHONPATH=...` inline on the same line (`PYTHONPATH=scripts/earnings $PY -m pytest ...`).
- `source venv/bin/activate` does NOT carry. Call the interpreter explicitly: `PY=/home/faisal/EventMarketDB/venv/bin/python` (worktree does NOT carry venv, the venv lives only in main; this is why `test_builders_warmup_cache.py` and `test_builders_cli_smoke.py` use `sys.executable` instead of a path under the worktree). All `Bash` blocks below define `PY` at the top of the block.
- `Edit` and `Write` MUST use the absolute path inside the worktree (`/home/faisal/em-warmup-cache-split/scripts/earnings/builders/...`) to avoid accidentally editing main.
- After every commit, run `cd /home/faisal/EventMarketDB && git status -s -- scripts/earnings/builders/warmup_cache.py scripts/earnings/builders/eight_k_packet.py scripts/earnings/builders/guidance_history.py scripts/earnings/builders/inter_quarter_context.py scripts/earnings/test_builders_imports.py scripts/earnings/test_builders_surface.py scripts/earnings/test_builders_static.py scripts/earnings/test_builders_warmup_cache.py scripts/earnings/test_builders_eight_k_packet.py scripts/earnings/test_builders_guidance_history.py scripts/earnings/test_builders_inter_quarter_context.py scripts/earnings/builders/README.md`. Expected output: empty (no unintended changes on main). If anything is non-empty, STOP and ask the user — do NOT auto-revert.

### 0.1 PYTHONPATH discipline (memorize this table)

| When you need to import this way… | Use this PYTHONPATH | Examples |
|---|---|---|
| Bare `import warmup_cache` in a FRESH process (no test framework) | `PYTHONPATH=.claude/skills/earnings-orchestrator/scripts:scripts/earnings:.` | Ad-hoc one-liners like `python -c "import warmup_cache; ..."`. The `.claude/skills/.../scripts` MUST come first because `warmup_cache.py` (the skill shim — bare-importable target) lives ONLY there, NOT under `scripts/earnings/`. `scripts/earnings` covers other bare imports (`peer_earnings_snapshot`, `build_consensus`, etc.); `.` covers qualified imports. |
| Bare imports inside `test_builders_*.py` (`import warmup_cache`, `from warmup_cache import build_8k_packet`, `import peer_earnings_snapshot`) | `PYTHONPATH=scripts/earnings` | The whole `test_builders_*.py` suite — these test files do their OWN `sys.path.insert(0, .claude/skills/.../scripts)` at import time (see `test_builders_imports.py:31`), so `PYTHONPATH=scripts/earnings` is sufficient at the pytest invocation level. Do NOT replicate the .claude path on PYTHONPATH for these — the test files handle it. |
| `python -m scripts.earnings.builders.warmup_cache ...` (any subcommand) | `PYTHONPATH=scripts/earnings` (or unset — cwd suffices) | The `-m` machinery resolves `scripts.earnings.builders.warmup_cache` via cwd's namespace package, then the module's `from ._paths import ensure_legacy_paths; ensure_legacy_paths()` adds the rest. PYTHONPATH=scripts/earnings is harmless extra precedence; cwd is what actually finds the module. |
| Qualified names ONLY (`from scripts.earnings.builders import _paths`) and you do NOT need bare imports | `PYTHONPATH=.` (i.e. repo root) | `test_builders_paths.py` is the canonical case — it imports `from scripts.earnings.builders import _paths` and nothing bare. |
| Both bare AND qualified in one process | `PYTHONPATH=scripts/earnings:.` (colon order: bare wins precedence) | Tests that mix `import warmup_cache` with `from scripts.earnings.builders.warmup_cache import ...` (e.g. the extended `test_parse_dt_for_pit_disambiguation` in Stage 3.2). The test file ALSO does its own `.claude/skills/.../scripts` insertion. |

When in doubt, copy the PYTHONPATH from the matching existing test file. Existing precedent (verified): `test_builders_paths.py` runs with `PYTHONPATH=.`; every other `test_builders_*.py` runs with `PYTHONPATH=scripts/earnings`. **Common gotcha:** in a fresh subprocess (e.g. `subprocess.run([PY, "-c", "..."])` from a test), the parent test file's `sys.path.insert` does NOT carry over — the subprocess needs the full `.claude/skills/.../scripts:scripts/earnings:.` triple, OR it must be invoked via `python -m scripts.earnings.builders.<X>` (qualified module path).

### 0.2 git-add discipline (every commit, every stage)

`git commit -m "..."` does NOT auto-stage modified or untracked files. Every commit MUST be preceded by an explicit `git add` of the in-scope files. The pattern for every stage is:

```bash
set -euo pipefail
cd /home/faisal/em-warmup-cache-split
git add <explicit list of paths edited or created in this stage>
git diff --cached --stat   # sanity-check what will be committed
git diff --cached --stat | grep -v "^ scripts/earnings/" \
    | grep -v "^ .claude/skills/earnings-orchestrator/" \
    && { echo "ERROR: out-of-scope file staged"; exit 1; } \
    || echo "OK: only in-scope files staged"
git commit -m "..."
```

NEVER use `git add -A` or `git add .` — both can sweep up `__pycache__`, stray editor state, or `.pytest_cache`. The per-stage commit-message blocks below list the exact `git add <files>` invocation for that stage.

### 0.3 Bash-pipeline hygiene (avoid silent failure-masking)

EVERY multi-command Gate Bash block in this plan MUST start with:

```bash
set -euo pipefail
```

Without `pipefail`, pipelines like `python ... 2>&1 | tee /tmp/foo.txt`, `pytest ... | sort | diff baseline -`, or `... | grep -oE 'pattern' | diff -` return the LAST command's exit code — a failing producer is silently masked by a successful consumer. With `pipefail`, the pipeline returns the FIRST non-zero exit code in the chain. `set -e` forces immediate exit on any error; `set -u` errors on unset vars (catches typos like `$PYY` instead of `$PY`). The §6.8 Required Gates block, every per-stage Gate, and the §9.4 post-merge gate all need this preamble — they all use piped invocations.

### 0.4 Edit-tool unique-string discipline

The plan's per-stage instructions sometimes describe a delete as "lines N–M" for human reference. The bot MUST NOT translate that into a fragile line-anchored Edit. The procedure for every delete is:

1. `Read` the file at the cited line range (`offset=N-2, limit=M-N+5`) to capture EXACT text including whitespace.
2. Construct `old_string` from the Read output, including 1–2 lines of unique surrounding context above AND below the block to delete (the surrounding context is what makes the match unique).
3. Set `new_string` to either empty (`""`) for pure delete, or the surrounding context with a 1-line replacement comment for delete-and-replace.
4. If the Edit fails with "old_string not unique", expand the surrounding context until uniqueness is achieved. Do NOT shorten the match.
5. Line numbers in the plan are SNAPSHOTS captured against the pre-flight state of `warmup_cache.py` (2066 lines). After each cutover the line numbers drift. The plan's anchors (function names, query-constant names, comment blocks) are stable; the line numbers are advisory.

---

## 1. Executive Decision

**Do the split.** Stage it as `COPY → CUTOVER` pairs per domain (Stages 1–3), preceded by a TDD foundation (Stage 0), followed by adapter-canonicalization (Stage 4 — REQUIRED, user-confirmed), final cleanup of unused imports (Stage 5), and a README update (Stage 6). Total = 10 commits.

**Do NOT do it as a single rewrite of `warmup_cache.py`.** The single-rewrite approach is unsafe because:

- `warmup_cache.py` has TWO independent personalities — extraction CLI (`run_warmup`, `run_transcript`, `run_mda`, `run_8k`) and orchestration builder (`build_8k_packet`, `build_guidance_history`, `build_inter_quarter_context`). They share `_fetch_8k_core` between `run_8k` and `build_8k_packet`. They share the CLI `main()` dispatcher. They share `_run_v2_regression_tests` invoked via `if __name__ == "__main__"`.
- Existing tests (`test_builder_validation.py:211/248/273/397/473/529/602/672`, `test_adapter_validation.py:341`) hard-code bare `from warmup_cache import ...` for the three domain functions and `_parse_dt_for_pit`.
- Existing adapter code in `scripts/earnings/builders/adapters.py` does `from scripts.earnings.builders.warmup_cache import build_8k_packet as _legacy` (and equivalents for the other two).
- The `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py` shim does `globals().update(dir(_impl))` over `scripts.earnings.builders.warmup_cache`, then `if __name__ == "__main__": sys.exit(0 if _impl._run_v2_regression_tests() else 1) ; _impl.main()`. Both `_run_v2_regression_tests` and `main` MUST remain reachable on `scripts.earnings.builders.warmup_cache`.
- `warmup_cache.sh` execs `python3 "$SCRIPT_DIR/warmup_cache.py" "$@"` — preserves the skill shim's CLI surface; the shell wrapper is unchanged.
- `.claude/references/prediction_context_bundle.md` has debug one-liners using `from builder_adapters import build_consensus, build_8k_packet, build_guidance_history, build_inter_quarter_context`.
- A simple rewrite would force every one of these consumers to know about the new module locations. The facade pattern reduces the blast radius to zero callers.

### 1.1 Target design (post-split)

```text
scripts/earnings/builders/
  _paths.py                          (UNCHANGED)
  __init__.py                        (UNCHANGED — still re-exports 7 adapters from .adapters)
  adapters.py                        (UNCHANGED through Stage 3; updated in Stage 4 to lazy-import from canonical domain home — included per user-confirmed plan choice)
  consensus.py                       (UNCHANGED)
  prior_financials.py                (UNCHANGED)
  macro_snapshot.py                  (UNCHANGED)
  peer_earnings_snapshot.py          (UNCHANGED)
  warmup_cache.py                    (FACADE — extraction modes + main() + re-export of domain symbols; ~520 lines after split)
  eight_k_packet.py                  (NEW — build_8k_packet + 8-K queries + _fetch_8k_core; ~150 lines)
  guidance_history.py                (NEW — build_guidance_history + render_guidance_text + guidance helpers + _run_v2_regression_tests; ~430 lines)
  inter_quarter_context.py           (NEW — build_inter_quarter_context + render_inter_quarter_text + IQ helpers + _parse_dt_for_pit; ~970 lines)
  README.md                          (UPDATED in Stage 6 — new layout table)
```

Final state: ONE canonical implementation per domain symbol. `warmup_cache.py` remains a facade that re-exports domain symbols by `is`-identity.

### 1.2 Naming rationale

- `eight_k_packet.py` — Python identifier rules forbid `8k_packet.py` as a module name (cannot start with a digit). `eight_k_packet` is the canonical Python-safe spelling that maps cleanly to the `8k_packet.v1` schema.
- `guidance_history.py` — matches `guidance_history.v1` schema and the orchestrator BUILDERS dict key `"guidance_history"`.
- `inter_quarter_context.py` — matches `inter_quarter_context.v1` schema and the orchestrator BUILDERS dict key `"inter_quarter_context"`.

The function names (`build_8k_packet`, `build_guidance_history`, `build_inter_quarter_context`) are unchanged — only the file housing them changes.

### 1.3 Re-export strategy (NOT wrapper functions)

`warmup_cache.py` re-exports the relocated symbols using direct module-level imports:

```python
from .eight_k_packet import (
    build_8k_packet,
    _fetch_8k_core,
    QUERY_4G_META,
    QUERY_4K_OTHER_PREVIEW,
    QUERY_4F,
    QUERY_4J,
    QUERY_4K,
)
from .guidance_history import (
    build_guidance_history,
    render_guidance_text,
    resolve_unit_groups,
    _format_value,
    _extract_given_day,
    _normalize_qualitative,
    _SOURCE_PRIORITY,
    QUERY_GUIDANCE_HISTORY,
    QUERY_GUIDANCE_HISTORY_PIT,
    _run_v2_regression_tests,
)
from .inter_quarter_context import (
    build_inter_quarter_context,
    render_inter_quarter_text,
    _parse_dt_for_pit,
    _is_price_pit_safe,
    _build_forward_returns,
    _iq_parse_json_field,
    _norm_ret,
    _fmt_vol,
    _fmt_txn,
    _safe_adj,
    _event_ref,
    _day_from_ts,
    _cutoff_boundary_price_role,
    _best_safe_horizon,
    _report_summary,
    _render_window_label_news,
    _render_window_label_filing,
    _render_horizon_line_filing,
    _render_news_react_line,
    QUERY_IQ_PRICES,
    QUERY_IQ_NEWS,
    QUERY_IQ_FILINGS,
    QUERY_IQ_DIVIDENDS,
    QUERY_IQ_SPLITS,
    QUERY_IQ_COMPANY_CONTEXT,
)
```

Direct re-export preserves Python `is`-identity by language guarantee: `from .X import foo` binds the SAME function object into `warmup_cache.foo`. Wrapper functions (`def build_8k_packet(*a, **kw): return _impl(*a, **kw)`) would create NEW function objects and silently break every identity test. The `globals().update()` shim mechanism used elsewhere in the migration is for DIFFERENT shim files (e.g. `scripts/earnings/builder_adapters.py`) — the warmup_cache facade is itself a real module, not a shim, so simple direct imports are correct here.

---

### 1.4 Non-Negotiable Invariants (must hold after every commit from Stage 1.2 onward)

These eight invariants are the contract. §11 risk table and §14 non-regression list both ladder up to them. If any one fails post-commit, STOP and rollback per the stage's "Rollback" subsection.

1. `from warmup_cache import build_8k_packet` (bare) still works inside `test_builders_*.py` (which manage their own `sys.path` to put `.claude/skills/.../scripts` first — see §0.1). For ad-hoc subprocess one-liners, the full triple `PYTHONPATH=.claude/skills/earnings-orchestrator/scripts:scripts/earnings:.` is required.
2. `from scripts.earnings.builders.warmup_cache import build_8k_packet` (qualified) still works.
3. `from scripts.earnings.builders.eight_k_packet import build_8k_packet` is the SAME object by `is`.
4. Same identity rule for `build_guidance_history` ↔ `guidance_history`, `build_inter_quarter_context` ↔ `inter_quarter_context`, `render_guidance_text`, `render_inter_quarter_text`, `_parse_dt_for_pit`, `_run_v2_regression_tests`, `_fetch_8k_core`.
5. `/home/faisal/EventMarketDB/venv/bin/python .claude/skills/earnings-orchestrator/scripts/warmup_cache.py --test` and `bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh --test` (which sources venv internally) keep working with unchanged pass count (baseline: 14 `check()` calls in `_run_v2_regression_tests`). RAW `python3` (system) lacks the `neo4j` package and would ImportError at warmup_cache load time — the venv interpreter is mandatory.
6. `_parse_dt_for_pit` remains DISTINCT from `peer_earnings_snapshot._parse_dt_for_pit` (`is not`). Same name, intentionally different functions.
7. `run_8k()` in warmup_cache keeps using the SAME shared `_fetch_8k_core()` object as `build_8k_packet()` in eight_k_packet (`wc._fetch_8k_core is ek._fetch_8k_core`).
8. All default `/tmp/...json` output paths, atomic-write behavior, schema versions, packet shapes, and rendered-text byte content stay equivalent except for the `assembled_at` timestamp (which is stripped before golden comparison).

---

## 2. Current-State Facts (verified against the repo)

```text
2066 scripts/earnings/builders/warmup_cache.py
  31 scripts/earnings/builders/__init__.py
  69 scripts/earnings/builders/_paths.py
 344 scripts/earnings/builders/adapters.py
1098 scripts/earnings/builders/consensus.py
1758 scripts/earnings/builders/prior_financials.py
 864 scripts/earnings/builders/macro_snapshot.py
 461 scripts/earnings/builders/peer_earnings_snapshot.py
  64 .claude/skills/earnings-orchestrator/scripts/warmup_cache.py    (skill CLI shim)
  27 .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh    (shell wrapper)
```

### 2.1 Symbol distribution inside `warmup_cache.py` today

| Lines | Symbol | Owns | Stays in `warmup_cache.py`? |
|---|---|---|---|
| 45–60 | `QUERY_2A` | extraction concept cache | **STAYS** (used by `run_warmup`) |
| 68–113 | `QUERY_2B` | extraction member cache (diagnostic) | **STAYS** (used by `run_warmup`) |
| 120–130 | `QUERY_MEMBER_MAP` | extraction member CIK lookup | **STAYS** (used by `run_warmup`) |
| 133–142 | `_build_member_map` | extraction member-map builder | **STAYS** (used by `run_warmup`) |
| 149–172 | `QUERY_3B` | extraction transcript content | **STAYS** (used by `run_transcript`) |
| 175–198 | `run_warmup` | extraction warmup CLI mode | **STAYS** |
| 201–211 | `run_transcript` | extraction transcript CLI mode | **STAYS** |
| 219–231 | `QUERY_5B` | extraction MD&A content | **STAYS** (used by `run_mda`) |
| 234–251 | `run_mda` | extraction MD&A CLI mode | **STAYS** |
| 258–262 | `QUERY_4J` | 8-K sections | **MOVES** to `eight_k_packet.py` (also used by `run_8k`) |
| 264–269 | `QUERY_4K` | 8-K EX-99 exhibits | **MOVES** to `eight_k_packet.py` (also used by `run_8k`) |
| 275–293 | `QUERY_4G_META` | 8-K metadata | **MOVES** to `eight_k_packet.py` |
| 298–305 | `QUERY_4K_OTHER_PREVIEW` | non-99 exhibit preview | **MOVES** to `eight_k_packet.py` |
| 310–313 | `QUERY_4F` | filing text fallback | **MOVES** to `eight_k_packet.py` |
| 321–343 | `QUERY_GUIDANCE_HISTORY` | guidance live | **MOVES** to `guidance_history.py` |
| 345–368 | `QUERY_GUIDANCE_HISTORY_PIT` | guidance PIT | **MOVES** to `guidance_history.py` |
| 371 | `_SOURCE_PRIORITY` | guidance source ordering | **MOVES** to `guidance_history.py` |
| 374–377 | `_extract_given_day` | guidance + IQ — `str(ts)[:10]` | **MOVES** to `guidance_history.py` (sole post-split caller is in render_guidance_text; IQ uses its own `_day_from_ts`) |
| 379–391 | `_normalize_qualitative` | guidance | **MOVES** to `guidance_history.py` |
| 393–417 | `resolve_unit_groups` | guidance | **MOVES** to `guidance_history.py` |
| 433–440 | `_fetch_8k_core` | shared by `run_8k` and `build_8k_packet` | **MOVES** to `eight_k_packet.py`; `warmup_cache.run_8k` re-imports it via the facade re-export so `_fetch_8k_core` identity is preserved across both call sites |
| 443–463 | `run_8k` | extraction 8-K CLI mode | **STAYS** (calls `_fetch_8k_core` via the facade re-export — same object) |
| 466–562 | `build_8k_packet` | orchestration 8-K packet | **MOVES** to `eight_k_packet.py` |
| 573–639 | `_format_value` | guidance render helper | **MOVES** to `guidance_history.py` |
| 642–702 | `render_guidance_text` | guidance render | **MOVES** to `guidance_history.py` |
| 705–929 | `build_guidance_history` | orchestration guidance | **MOVES** to `guidance_history.py` |
| 940–1068 | `QUERY_IQ_*` (6 queries) | inter-quarter | **MOVES** to `inter_quarter_context.py` |
| 1073–1126 | `_iq_parse_json_field`, `_norm_ret`, `_fmt_vol`, `_fmt_txn`, `_safe_adj`, `_event_ref`, `_day_from_ts` | IQ helpers | **MOVE** to `inter_quarter_context.py` |
| 1128–1143 | `_parse_dt_for_pit` | IQ helper (also a name shared with `peer_earnings_snapshot._parse_dt_for_pit` — DIFFERENT function) | **MOVES** to `inter_quarter_context.py` |
| 1146–1158 | `_is_price_pit_safe` | IQ helper | **MOVES** to `inter_quarter_context.py` |
| 1160–1210 | `_build_forward_returns` | IQ helper | **MOVES** to `inter_quarter_context.py` |
| 1213–1221 | `_cutoff_boundary_price_role` | IQ helper | **MOVES** to `inter_quarter_context.py` |
| 1223–1235 | `_best_safe_horizon` | IQ render helper | **MOVES** to `inter_quarter_context.py` |
| 1238–1247 | `_report_summary` | IQ render helper | **MOVES** to `inter_quarter_context.py` |
| 1253–1320 | `_render_window_label_news`, `_render_window_label_filing`, `_render_horizon_line_filing`, `_render_news_react_line` | IQ render helpers | **MOVE** to `inter_quarter_context.py` |
| 1323–1493 | `render_inter_quarter_text` | IQ render | **MOVES** to `inter_quarter_context.py` |
| 1496–1879 | `build_inter_quarter_context` | orchestration IQ | **MOVES** to `inter_quarter_context.py` |
| 1882–2000 | `main()` | CLI dispatch (8 modes) | **STAYS** — all 8 mode branches keep working because `build_8k_packet`, `build_guidance_history`, `build_inter_quarter_context`, `render_guidance_text`, `render_inter_quarter_text` are still reachable via `warmup_cache.X` (re-exported) |
| 2003–2060 | `_run_v2_regression_tests` | guidance unit tests | **MOVES** to `guidance_history.py` (it tests `_format_value` + `resolve_unit_groups`; that's the natural home). Re-exported from `warmup_cache.py` so `if __name__ == "__main__": sys.exit(0 if _run_v2_regression_tests() else 1)` still works through every CLI path. |
| 2063–2065 | `if __name__ == "__main__"` block — pre-`main()` `--test` dispatch | **STAYS** — invokes the re-exported `_run_v2_regression_tests` |

After the split, `warmup_cache.py` will contain (from top to bottom): module docstring, stdlib imports, `_paths.ensure_legacy_paths()`, `from neograph.Neo4jConnection import get_manager`, the four re-export blocks (one per domain module), `QUERY_2A/2B/MEMBER_MAP/3B/5B`, `_build_member_map`, `run_warmup`, `run_transcript`, `run_mda`, `run_8k`, `main()`, `if __name__ == "__main__"` block. Estimated ~520 lines.

### 2.2 External consumers of relocated symbols (verified)

A. **Public functions (`build_*`, `render_*`):**

| Consumer | Line | How |
|---|---|---|
| `scripts/earnings/builders/adapters.py` | 115, 152, 183 | lazy `from scripts.earnings.builders.warmup_cache import build_X as _legacy` (3 sites) |
| `scripts/earnings/test_builder_validation.py` | 211, 248, 273, 397, 473, 529, 672 | bare `from warmup_cache import build_X` (7 sites) |
| `scripts/earnings/test_adapter_validation.py` | 341 | bare `from warmup_cache import build_8k_packet as legacy_8k` |
| `scripts/earnings/test_builders_adapters.py` | 42 | `patch("scripts.earnings.builders.warmup_cache.build_8k_packet", ...)` |
| `scripts/earnings/test_builders_warmup_cache.py` | 31, 33–34 | `from scripts.earnings.builders import warmup_cache as wc; assert hasattr(wc, ...)` (10 symbols including all 5 public + 2 private) |
| `scripts/earnings/test_builders_imports.py` | 64–70 | `MODULE_PAIRS["warmup_cache"]` — 12 symbols (parametrized identity test) |
| `scripts/earnings/test_builders_surface.py` | 37–43 | `EXPECTED_SURFACE["warmup_cache"]` — 10 public + 2 private |
| `scripts/earnings/test_builders_imports.py` | 205–217 | `test_parse_dt_for_pit_disambiguation` — `import warmup_cache; warmup_cache._parse_dt_for_pit` |
| `.claude/references/prediction_context_bundle.md` | 288, 294, 312, 330 | bare `from builder_adapters import build_X` debug one-liners (use the adapter facade, not warmup_cache directly — but still depend on the chain working) |
| `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py` | 43, 46–48, 62 | shim re-exports ALL non-dunder names from `scripts.earnings.builders.warmup_cache`; `__main__` calls `_impl._run_v2_regression_tests` then `_impl.main()` |
| `.claude/skills/earnings-orchestrator/scripts/warmup_cache.sh` | 27 | execs the skill shim; pure CLI passthrough |
| Skill markdown (4 files under `.claude/skills/extract/types/guidance/`) | various | `bash .../warmup_cache.sh ARGS` — only depends on shell wrapper + skill shim staying alive |

Every one of these resolves correctly through the facade re-export. No caller-side change is required.

B. **Private helpers reachable by name:**

| Symbol | External consumer | Verified by `rg` |
|---|---|---|
| `_parse_dt_for_pit` | `test_builder_validation.py:602`, `test_builders_imports.py:205,209,214,215`, `test_builders_surface.py:42` | YES — must remain reachable via `warmup_cache._parse_dt_for_pit` AND must remain `is not peer_earnings_snapshot._parse_dt_for_pit` |
| `_run_v2_regression_tests` | `test_builders_warmup_cache.py:36`, `test_builders_surface.py:42`, `.claude/skills/.../warmup_cache.py:63` | YES — must remain reachable via `warmup_cache._run_v2_regression_tests` |
| `_fetch_8k_core` | `warmup_cache.run_8k` (line 451) | INTERNAL — but identity must hold across `run_8k` and `build_8k_packet` callers (the shared-ownership comment block at lines 423–431 documents this contract) |
| `_format_value`, `resolve_unit_groups`, `_normalize_qualitative`, `_extract_given_day`, `_SOURCE_PRIORITY`, `_iq_parse_json_field`, `_norm_ret`, `_fmt_vol`, `_fmt_txn`, `_safe_adj`, `_event_ref`, `_day_from_ts`, `_is_price_pit_safe`, `_build_forward_returns`, `_cutoff_boundary_price_role`, `_best_safe_horizon`, `_report_summary`, `_render_*` (4 funcs) | NONE outside `warmup_cache.py` (verified: `rg --include="*.py" --include="*.sh"` finds only doc-references in `.claude/plans/planner.md`, `plannerStep5.md`, `earnings-orchestrator.md`; no Python import) | Helpers are free to move; only need to remain importable from their canonical domain home for the new domain-module unit tests |

C. **Symbols that STAY in `warmup_cache.py` and must keep working:**

`QUERY_2A`, `QUERY_2B`, `QUERY_MEMBER_MAP`, `QUERY_3B`, `QUERY_5B`, `_build_member_map`, `run_warmup`, `run_transcript`, `run_mda`, `run_8k`, `main`. None of these is referenced externally except via the CLI (`warmup_cache.sh` and `python -m scripts.earnings.builders.warmup_cache`).

D. **`_fetch_8k_core` shared-ownership note (CRITICAL):**

The comment block at `warmup_cache.py:420–431` documents that `_fetch_8k_core` is shared between `run_8k` (extraction) and `build_8k_packet` (orchestration). After the split:

- The canonical home of `_fetch_8k_core` is `scripts.earnings.builders.eight_k_packet`.
- `warmup_cache.run_8k` calls it via the facade re-export — same Python object, same behavior.
- The shared-ownership comment block MUST move into `eight_k_packet.py`, with text updated to reflect the new module layout. A short cross-reference comment near `warmup_cache.run_8k` (something like `# _fetch_8k_core lives in eight_k_packet; we re-export it above and call the SAME object`) is encouraged but not required.

### 2.3 Existing TDD scaffolding (load-bearing, MUST be extended NOT replaced)

| File | Lines | Role |
|---|---|---|
| `scripts/earnings/test_builders_paths.py` | 192 | `_paths.py` API + idempotence + utils-shadow regression. UNCHANGED by this plan. |
| `scripts/earnings/test_builders_surface.py` | 65 | `EXPECTED_SURFACE` per module — symbols MUST be reachable. **NOT EXTENDED** by this plan. The existing `warmup_cache` row stays UNCHANGED. **Do NOT add `eight_k_packet` / `guidance_history` / `inter_quarter_context` rows** — that dict is bare-import-keyed (`importlib.import_module("eight_k_packet")` would fail; the canonical home is `scripts.earnings.builders.eight_k_packet`) AND `test_module_pairs_completeness` would also fail without matching MODULE_PAIRS rows. Per-domain surface coverage lives in `test_builders_warmup_split.py` parametrize lists. |
| `scripts/earnings/test_builders_imports.py` | 405 | `MODULE_PAIRS` 4-path identity. **NOT EXTENDED** with new domain rows (the parametrize there assumes "old bare path" is a real import target). Stages 1.2/2.2/3.2 add 3 STAND-ALONE identity tests (`test_eight_k_packet_canonical_facade_identity`, etc.) that don't go through `MODULE_PAIRS`. Existing `warmup_cache` row UNCHANGED. `test_parse_dt_for_pit_disambiguation` EXTENDED to also assert distinctness against `inter_quarter_context._parse_dt_for_pit` and identity through facade. `test_concurrent_imports_preserve_identity` EXTENDED — `mods_to_import` gains 3 entries (one per domain module). |
| `scripts/earnings/test_builders_static.py` | 116 | AST shim guard. UNCHANGED — `warmup_cache.py` is NOT a shim (it's a facade with real CLI code), so it does NOT belong in `SHIM_FILES`. The new domain modules are also NOT shims. |
| `scripts/earnings/test_builders_warmup_cache.py` | 47 | `--test` invocation + neograph import smoke + 12-symbol surface check. UNCHANGED — every listed symbol still reachable via the facade. |
| `scripts/earnings/test_builders_cli_smoke.py` | 62 | `warmup_cache.py --test` (skill shim) and `warmup_cache.sh --test`. UNCHANGED. |
| `scripts/earnings/test_builders_adapters.py` | 64 | Adapter mocking. The `patch("scripts.earnings.builders.warmup_cache.build_8k_packet", ...)` target is correct AS LONG AS the adapter still imports from `warmup_cache`. If Stage 4 (canonicalization) is executed, this patch target updates to `scripts.earnings.builders.eight_k_packet.build_8k_packet`. |

NEW test files added by this plan:

- `scripts/earnings/test_builders_eight_k_packet.py` — Stage 1.1
- `scripts/earnings/test_builders_guidance_history.py` — Stage 2.1
- `scripts/earnings/test_builders_inter_quarter_context.py` — Stage 3.1
- `scripts/earnings/test_builders_warmup_split.py` — Stage 0 (golden-equivalence + facade-identity contract harness)

---

## 3. Migration Scope

### In scope

- Add `scripts/earnings/builders/eight_k_packet.py` containing `build_8k_packet`, `_fetch_8k_core`, `QUERY_4G_META`, `QUERY_4K_OTHER_PREVIEW`, `QUERY_4F`, `QUERY_4J`, `QUERY_4K`.
- Add `scripts/earnings/builders/guidance_history.py` containing `build_guidance_history`, `render_guidance_text`, `_format_value`, `resolve_unit_groups`, `_extract_given_day`, `_normalize_qualitative`, `_SOURCE_PRIORITY`, `QUERY_GUIDANCE_HISTORY`, `QUERY_GUIDANCE_HISTORY_PIT`, `_run_v2_regression_tests`.
- Add `scripts/earnings/builders/inter_quarter_context.py` containing `build_inter_quarter_context`, `render_inter_quarter_text`, `_parse_dt_for_pit`, `_is_price_pit_safe`, `_build_forward_returns`, `_iq_parse_json_field`, `_norm_ret`, `_fmt_vol`, `_fmt_txn`, `_safe_adj`, `_event_ref`, `_day_from_ts`, `_cutoff_boundary_price_role`, `_best_safe_horizon`, `_report_summary`, `_render_window_label_news`, `_render_window_label_filing`, `_render_horizon_line_filing`, `_render_news_react_line`, all 6 `QUERY_IQ_*` constants.
- Convert `scripts/earnings/builders/warmup_cache.py` to a facade that re-exports every relocated symbol via direct module-level imports (NOT wrappers).
- Add per-domain mocked unit test files (`test_builders_eight_k_packet.py`, `test_builders_guidance_history.py`, `test_builders_inter_quarter_context.py`).
- Add the contract-test harness (`test_builders_warmup_split.py`) covering: golden structural-equality between pre-split snapshots and post-split outputs (FIVE 8-K, FIVE guidance, FIVE inter-quarter); facade-vs-canonical identity for every relocated symbol; no `warmup_cache` back-imports inside the new domain modules.
- Add 3 stand-alone facade-vs-canonical identity tests to `test_builders_imports.py` (one per new domain — `test_eight_k_packet_canonical_facade_identity`, `test_guidance_history_canonical_facade_identity`, `test_inter_quarter_context_canonical_facade_identity`). Do NOT add new `MODULE_PAIRS` rows or `EXPECTED_SURFACE` entries — see §2.3.
- Extend `test_parse_dt_for_pit_disambiguation` (in `test_builders_imports.py`) to also assert distinctness against the new canonical `inter_quarter_context._parse_dt_for_pit` path.
- Extend `test_concurrent_imports_preserve_identity::mods_to_import` with the 3 new canonical domain module paths (one per Stage 1.2/2.2/3.2 cutover).
- Stage 4 (REQUIRED — user-confirmed): Update `adapters.py` lazy imports to point at canonical domain modules; update `test_builders_adapters.py:42` patch target accordingly.
- Final cleanup of unused imports in `warmup_cache.py` (`math`, `Counter`, `defaultdict` — all only used by relocated code).
- Update `scripts/earnings/builders/README.md` with the new layout.

### Out of scope

- **Do NOT change builder behavior, packet schemas, atomic-write semantics, output paths, retry policy, source policy, or any rendered-text format.** This is pure relocation — the function bodies are byte-identical except for import lines that reference newly-local helpers.
- **Do NOT rename any function, class, query constant, or helper.** Only file location changes.
- **Do NOT split `warmup_cache.py`'s extraction-side code** (`run_warmup`, `run_transcript`, `run_mda`, `run_8k`) into separate modules. Out of scope for this PR.
- **Do NOT delete `warmup_cache.py`.** It is a permanent facade — it owns the extraction CLI and the `--8k`/`--mda`/`--transcript`/etc. dispatchers, and it is the import entry point for adapters and external tests.
- **Do NOT change `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py` shim** (still wraps `scripts.earnings.builders.warmup_cache`).
- **Do NOT change `warmup_cache.sh`.** Behavior preserved through the unchanged shim.
- **Do NOT modify any existing test file's import style.** Tests stay on `from warmup_cache import build_X` — they ARE the regression coverage that proves the facade works.
- **Do NOT consolidate `_parse_dt_for_pit`** with `peer_earnings_snapshot._parse_dt_for_pit`. Same name, different implementations is intentional. The shadow guard test must still pass.
- **Do NOT touch K8s, KEDA, Docker images, or `.env`.** None of those depend on intra-package layout.
- **Do NOT bundle docs migration.** `.claude/plans/planner.md`, `plannerStep5.md`, `earnings-orchestrator.md` reference the helpers by name in prose — those references remain accurate (function signatures unchanged) and need no edits. The `.claude/plans/warmup_cache_restructure.md` outline becomes historical; this plan supersedes it but does not delete the file.
- **Do NOT update `MEMORY.md`** unless the user asks. Memory is for cross-session learnings, not implementation traces.

---

## 4. Risk Model

### 4.1 Highest-risk area: identity preservation through the facade

`warmup_cache.py` becoming a facade means every relocated symbol is reached via re-export. Python's `from X import Y` binds the SAME object — so `is`-identity is preserved by construction. **But** if anyone later inserts `def build_8k_packet(*a, **kw): return _impl(*a, **kw)` between the import and the user, identity breaks silently.

Mitigation:

- The new test `test_facade_reexports_match_eight_k_packet_canonical` (and equivalents) asserts `getattr(warmup_cache, sym) is getattr(eight_k_packet, sym)` for every relocated symbol. This test runs in every per-stage gate from Stage 1.2 onward.
- The existing 4-path identity test (`test_old_bare_equals_new_qualified` in `test_builders_imports.py`) continues to assert `warmup_cache.X is scripts.earnings.builders.warmup_cache.X` — so a bare-import caller and a qualified-import caller still get the same object.
- AST static guard does NOT apply (warmup_cache.py is a facade with real CLI code, not a shim) — but the `test_facade_has_no_relocated_function_defs` static check (added in Stage 0, gated on `_all_reexport_blocks_present()` so it activates at Stage 3.2 cutover) parses warmup_cache.py and asserts NO `def` for any name in `_RELOCATED_FUNCTIONS` (build_8k_packet, build_guidance_history, build_inter_quarter_context, render_guidance_text, render_inter_quarter_text, _parse_dt_for_pit, _format_value, resolve_unit_groups, _build_forward_returns, plus the rest of the relocated helpers). The chosen gate keeps the assertion firing on regression — re-export blocks remain even if a stray def is added back, so the test fails LOUDLY rather than silently skipping.

### 4.2 Cross-module shadow risk (`_parse_dt_for_pit`)

`peer_earnings_snapshot._parse_dt_for_pit` and `warmup_cache._parse_dt_for_pit` are SAME-NAMED but DIFFERENT functions. After the split, the canonical home of warmup's version becomes `inter_quarter_context._parse_dt_for_pit`. The peer version is unchanged.

Required invariants after Stage 3.2:

```text
warmup_cache._parse_dt_for_pit
  is scripts.earnings.builders.warmup_cache._parse_dt_for_pit
  is scripts.earnings.builders.inter_quarter_context._parse_dt_for_pit
  is NOT peer_earnings_snapshot._parse_dt_for_pit
  is NOT scripts.earnings.builders.peer_earnings_snapshot._parse_dt_for_pit
```

Mitigation: extend the existing `test_parse_dt_for_pit_disambiguation` (in `test_builders_imports.py:190–218`) with explicit asserts for the canonical `inter_quarter_context` path. See Stage 3.2 edit instructions.

### 4.3 `_run_v2_regression_tests` invocation chain

The `--test` CLI invocation chain passes through three files:

1. `bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh --test`
2. → `/home/faisal/EventMarketDB/venv/bin/python .claude/skills/earnings-orchestrator/scripts/warmup_cache.py --test` (the venv interpreter is mandatory — system `python3` lacks the `neo4j` package)
3. → `_impl._run_v2_regression_tests()` where `_impl` is `scripts.earnings.builders.warmup_cache` (per shim line 43)
4. → after the split, `_run_v2_regression_tests` is re-exported from `scripts.earnings.builders.guidance_history`. Identity is preserved by direct import.

Mitigation:

- `test_builders_cli_smoke.py:test_cli_warmup_cache_test_flag` and `test_cli_warmup_cache_sh_test_flag` continue to be run in every per-stage gate.
- `test_builders_warmup_cache.py:test_module_test_flag_passes` runs `python -m scripts.earnings.builders.warmup_cache --test` and asserts exit code 0 with "passed" in output. Continues to be run in every per-stage gate.

### 4.4 `_fetch_8k_core` shared between `run_8k` and `build_8k_packet`

After the split, `_fetch_8k_core` lives in `eight_k_packet.py`. `warmup_cache.run_8k` calls it. The simplest correct pattern: warmup_cache imports it as part of the eight_k_packet re-export block, and `run_8k`'s body uses `_fetch_8k_core(manager, accession)` (unqualified) — same object resolved through warmup_cache's globals.

Edge case: do NOT add a defensive local import inside `run_8k` (e.g. `from .eight_k_packet import _fetch_8k_core`). That works but obscures the contract. Use the module-level re-export.

Mitigation:

- A NEW unit test `test_run_8k_uses_canonical_fetch_8k_core` is added in **Stage 1.2** (NOT Stage 1.1 — it cannot pass during COPY-only when both modules have their own def). The test is identity-only; do NOT use `mock.patch("scripts.earnings.builders.eight_k_packet._fetch_8k_core")` and then call `wc.run_8k(...)` — the patch would NOT take effect (see §10.16 mock-patch precedence asymmetry). Correct test:
  ```python
  import scripts.earnings.builders.warmup_cache as wc
  import scripts.earnings.builders.eight_k_packet as ek
  assert wc._fetch_8k_core is ek._fetch_8k_core
  # __globals__ assertion proves run_8k's name lookup goes through the right namespace
  assert wc.run_8k.__globals__["_fetch_8k_core"] is ek._fetch_8k_core
  ```
  See Stage 1.2 step 8 for the full test source with rationale.

### 4.5 No-cycle invariant

The new domain modules MUST NOT import `warmup_cache`. If they do, the import graph forms a cycle (`warmup_cache → eight_k_packet → warmup_cache`) that resolves at import time but creates non-deterministic ordering issues for `from .X import ...` patterns.

Mitigation:

- A NEW static test in `test_builders_warmup_split.py:test_no_warmup_cache_back_imports` parses each domain module's AST and asserts no `from .warmup_cache import` or `import warmup_cache` appears.
- All shared helpers go DOWN (warmup_cache imports from domain modules, never the reverse). The only "shared" symbol between extraction and orchestration paths today is `_fetch_8k_core`, which moves DOWN to `eight_k_packet.py`.

### 4.6 Path math (NOT a risk)

`_paths.py` is unchanged. The new domain modules sit at the SAME depth as `consensus.py`, `prior_financials.py`, etc. (`scripts/earnings/builders/<X>.py`), so `parents[3]` repo-root math (used inside `_paths.py`) continues to work. Each new domain module starts with `from ._paths import ensure_legacy_paths; ensure_legacy_paths()`, identical to existing builders. The static guard `! rg -n "parents\[2\]|/home/faisal/EventMarketDB" scripts/earnings/builders/<just-moved>.py` should yield zero hits per stage.

### 4.7 Live services (not tested per-stage)

Builder execution touches Neo4j. Per-stage gates use mocked Neo4j (the `manager.execute_cypher_query_all` is patched). Live validation (`test_builder_validation.py --ticker FIVE` and `test_adapter_validation.py --ticker FIVE`) does NOT run per-stage but IS REQUIRED as the final pre-merge or post-merge gate (see §12 done criteria + §14 acceptance bar). A Neo4j-unavailable skip is NOT a passing condition — re-run with connectivity restored, or record an explicit user-approved waiver in the PR description. The `--test` CLI mode is fully self-contained (no network) and CAN run per-stage.

### 4.8 Concurrent-import semantics during cutover commits (asymmetry note)

Each cutover commit (Stage 1.2 / 2.2 / 3.2) ATOMICALLY changes `warmup_cache.py` from "owns def X" to "imports X from .domain_module". A reader might wonder whether the §9.1 quiescence check (Redis queue empty + no extraction-worker pods) should be applied PER stage as well. The answer is **no**:

- Stage commits land in the worktree (`/home/faisal/em-warmup-cache-split/...`). The hostPath mount that production extraction-worker pods read from is `/home/faisal/EventMarketDB` (main repo). The two paths are distinct working trees — git worktree gives each its own checkout. So a stage commit in the worktree NEVER changes a file the production pods see.
- The §9.1 quiescence check applies ONLY at MERGE time (when `git merge --ff-only` rewrites files in the main repo). That's when production-visible files change — and that's when the check is mandatory.

If a future maintainer wonders "wait, do I quiesce per stage?" — the answer is no, but only because the worktree isolation makes per-stage commits invisible to production.

---

## 5. Compatibility Re-Export Requirements

### 5.1 The facade re-export contract

`scripts/earnings/builders/warmup_cache.py` becomes a hybrid module: it owns the extraction-side functions and CLI dispatcher AND re-exports every symbol relocated to a domain module. The contract is:

> Every name listed in `EXPECTED_SURFACE["warmup_cache"]` (10 public + 2 private) AND every helper that any other test or production file references via `warmup_cache.X` MUST resolve via Python `is` to the SAME object as the canonical-domain symbol.

Mechanism: direct `from .X import sym` at module level. Example:

```python
# In warmup_cache.py, after the stdlib imports + ensure_legacy_paths() + neograph import:

# ── Domain modules — relocated symbols re-exported here for back-compat ──
from .eight_k_packet import (
    build_8k_packet,
    _fetch_8k_core,
    QUERY_4J,
    QUERY_4K,
    QUERY_4G_META,
    QUERY_4K_OTHER_PREVIEW,
    QUERY_4F,
)
from .guidance_history import (
    build_guidance_history,
    render_guidance_text,
    resolve_unit_groups,
    _format_value,
    _extract_given_day,
    _normalize_qualitative,
    _SOURCE_PRIORITY,
    QUERY_GUIDANCE_HISTORY,
    QUERY_GUIDANCE_HISTORY_PIT,
    _run_v2_regression_tests,
)
from .inter_quarter_context import (
    build_inter_quarter_context,
    render_inter_quarter_text,
    _parse_dt_for_pit,
    _is_price_pit_safe,
    _build_forward_returns,
    _iq_parse_json_field,
    _norm_ret,
    _fmt_vol,
    _fmt_txn,
    _safe_adj,
    _event_ref,
    _day_from_ts,
    _cutoff_boundary_price_role,
    _best_safe_horizon,
    _report_summary,
    _render_window_label_news,
    _render_window_label_filing,
    _render_horizon_line_filing,
    _render_news_react_line,
    QUERY_IQ_PRICES,
    QUERY_IQ_NEWS,
    QUERY_IQ_FILINGS,
    QUERY_IQ_DIVIDENDS,
    QUERY_IQ_SPLITS,
    QUERY_IQ_COMPANY_CONTEXT,
)
```

The block grows incrementally — only `eight_k_packet` symbols are added in Stage 1.2; `guidance_history` symbols in Stage 2.2; `inter_quarter_context` symbols in Stage 3.2.

### 5.2 Why this approach (not wrapper functions)

A wrapper function (`def build_8k_packet(*a, **kw): return _impl.build_8k_packet(*a, **kw)`) creates a NEW callable object. The 4-path identity invariant (`from warmup_cache import build_8k_packet is from eight_k_packet import build_8k_packet`) FAILS, breaking every existing identity test. The orchestrator and adapters call the function — they do not introspect identity — so wrappers would APPEAR to work. But the silent identity break would degrade the safety contract that the rest of the builders subpackage relies on for cross-path consistency. Direct re-export is the correct and minimal pattern.

### 5.3 Why the existing `globals().update(dir(_impl))` shim mechanism is NOT used here

`scripts/earnings/builder_adapters.py`, `scripts/earnings/build_consensus.py`, `.claude/skills/.../warmup_cache.py`, etc. use the `globals().update()` loop because those files are SHIMS for files that already exist as full implementations elsewhere. They have no business logic of their own — they exist purely to bridge OLD import paths to the canonical NEW location.

`warmup_cache.py` is DIFFERENT. After the split it is a real, working module that owns the extraction CLI (`run_warmup`, `run_transcript`, etc.) and the dispatcher (`main`). It imports specific symbols from each domain module. Direct `from .X import Y` is the natural Python-idiomatic pattern. Using `globals().update()` here would (a) be a wholesale dump of every name from each domain module — including helpers that have no external consumer and pollute warmup_cache's namespace; (b) be incorrect because warmup_cache also has its OWN top-level symbols (`run_warmup`, `QUERY_2A`, etc.) that would collide if any domain module ever defined a same-named symbol.

### 5.4 Shim files outside `scripts/earnings/builders/`

The skill shim `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py` is unchanged. It already does:

```python
from scripts.earnings.builders import warmup_cache as _impl
for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)
__all__ = [_name for _name in dir(_impl) if not _name.startswith("_")]
del _name
```

Because the facade re-exports relocated symbols into its OWN globals, `dir(_impl)` includes every relocated name AND every extraction-side name AND `_run_v2_regression_tests`. The skill shim's `globals().update(dir(_impl))` therefore captures everything — including the relocated symbols — by the SAME object identity. No edit required in the skill shim.

The `__main__` block of the skill shim:

```python
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        sys.exit(0 if _impl._run_v2_regression_tests() else 1)
    _impl.main()
```

`_impl._run_v2_regression_tests` resolves to `scripts.earnings.builders.warmup_cache._run_v2_regression_tests` which is the re-exported binding from `guidance_history`. Identity preserved. `_impl.main` resolves to the unchanged `main()` function in `warmup_cache.py`. Both work without edit.

---

## 6. Pre-Flight Verification

Run BEFORE creating the worktree. If any check fails, STOP and ask the user.

```bash
set -euo pipefail
cd /home/faisal/EventMarketDB
PY=/home/faisal/EventMarketDB/venv/bin/python

# 6.1 — On main, no uncommitted changes to in-scope files
git status -s -- scripts/earnings/builders/warmup_cache.py \
    scripts/earnings/builders/__init__.py \
    scripts/earnings/builders/adapters.py \
    scripts/earnings/builders/_paths.py \
    scripts/earnings/builders/README.md \
    scripts/earnings/test_builders_imports.py \
    scripts/earnings/test_builders_surface.py \
    scripts/earnings/test_builders_static.py \
    scripts/earnings/test_builders_warmup_cache.py \
    scripts/earnings/test_builders_paths.py \
    scripts/earnings/test_builders_cli_smoke.py \
    scripts/earnings/test_builders_adapters.py \
    .claude/skills/earnings-orchestrator/scripts/warmup_cache.py \
    .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh
# expect: empty output

# 6.2 — Baseline tests pass on main
PYTHONPATH=. $PY -m pytest scripts/earnings/test_builders_paths.py -q
# expect: 12 passed
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_*.py -q -m "not live"
# expect: 165 passed (or whatever the current Stage 15 baseline is — capture it)

# 6.3 — CLI --test passes on main; LOCK IN the baseline pass count for later diff.
#       The post-cutover gate must show the SAME count (currently 14). If it drifts,
#       _run_v2_regression_tests lost or gained a check() during the move.
PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache --test 2>&1 \
    | tee /tmp/warmup_split_test_baseline.txt
grep -oE '[0-9]+ passed, [0-9]+ failed out of [0-9]+' /tmp/warmup_split_test_baseline.txt \
    > /tmp/warmup_split_test_count_baseline.txt
cat /tmp/warmup_split_test_count_baseline.txt
# expect: "14 passed, 0 failed out of 14"
# (The §6.8 Required Gates block diffs against this baseline after every cutover.)

PYTHONPATH=scripts/earnings $PY .claude/skills/earnings-orchestrator/scripts/warmup_cache.py --test
# expect: same "14 passed, 0 failed out of 14" output
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh --test
# expect: same output

# 6.4 — Capture current line count + symbol inventory of warmup_cache.py
wc -l scripts/earnings/builders/warmup_cache.py
# expect: 2066

PYTHONPATH=scripts/earnings:. $PY -c "
import scripts.earnings.builders.warmup_cache as wc
from test_builders_surface import EXPECTED_SURFACE
syms = sorted(EXPECTED_SURFACE['warmup_cache']['public'] +
              EXPECTED_SURFACE['warmup_cache']['private_exports'])
for s in syms:
    obj = getattr(wc, s, None)
    print(f'{s:32s} id={id(obj):16x} type={type(obj).__name__}')
" | tee /tmp/warmup_split_baseline_identity.txt

# /tmp/warmup_split_baseline_identity.txt is the baseline identity TABLE for human reference.
# Each id() WILL change after the split (relocated symbols become re-exports, getting new module-level
# cells in the canonical domain module). The contract is identity ACROSS PATHS within a single Python
# process, not absolute id() stability across processes. Save the per-symbol TYPE column though —
# QUERY_* must remain `str`, helpers `function`. A type drift indicates a wrapping mistake.

# 6.5 — Worktree + branch don't already exist
test -d /home/faisal/em-warmup-cache-split && echo "ERROR: worktree exists" || echo "OK: worktree absent"
git branch --list warmup-cache-domain-split | grep . && echo "ERROR: branch exists" || echo "OK: branch absent"

# 6.6 — Repo HEAD context (capture for the rollback tag)
git rev-parse HEAD
git log -1 --oneline
```

If all of 6.1–6.6 pass, create the worktree:

```bash
set -euo pipefail
cd /home/faisal/EventMarketDB
git worktree add /home/faisal/em-warmup-cache-split -b warmup-cache-domain-split main
ls -la /home/faisal/em-warmup-cache-split/scripts/earnings/builders/warmup_cache.py
# expect: file exists at expected path

# Capture renderer-suite test names BEFORE any change so the consolidated gate (§6.8)
# can diff against this baseline and catch silent name drift (count-preserving renames).
PYTHONPATH=scripts/earnings /home/faisal/EventMarketDB/venv/bin/python \
    -m pytest scripts/earnings/test_renderer_*.py --collect-only -q | sort \
    > /tmp/renderer_tests_before.txt
wc -l /tmp/renderer_tests_before.txt
```

The worktree does NOT carry `venv/` (gitignored). Use `PY=/home/faisal/EventMarketDB/venv/bin/python` for every Python invocation in the worktree — the interpreter resolves modules via `PYTHONPATH=...`, NOT via the venv's own site-packages, so the main-repo venv works correctly when invoked with explicit `PYTHONPATH`. Existing tests (`test_builders_warmup_cache.py:11`, `test_builders_cli_smoke.py:20`) follow the same pattern (`PY = sys.executable` — meaning they use whatever interpreter pytest was invoked with, which is the main-repo venv).

### 6.7 .env symlink (REQUIRED — not optional)

Live tests (Stage 5 goldens AND the REQUIRED final-validation `test_builder_validation.py --ticker FIVE` and `test_adapter_validation.py --ticker FIVE` — see §4.7, §12 done criteria, §14 acceptance bar) rely on `.env` for Neo4j credentials. The worktree does NOT carry `.env` (it's gitignored). Symlink it from main:

```bash
set -euo pipefail
test -L /home/faisal/em-warmup-cache-split/.env \
    && echo "OK: .env symlink present" \
    || ln -s /home/faisal/EventMarketDB/.env /home/faisal/em-warmup-cache-split/.env
test -L /home/faisal/em-warmup-cache-split/.env \
    && echo "OK: .env symlink created/verified" \
    || { echo "ERROR: could not symlink .env"; exit 1; }
```

The worktree ALSO does NOT carry `venv/` (gitignored). `warmup_cache.sh:24` does `source "$REPO_ROOT/venv/bin/activate"` where `$REPO_ROOT` is the worktree, so the bash test wrapper fails without a venv symlink. Same pattern as `.env`:

```bash
set -euo pipefail
test -L /home/faisal/em-warmup-cache-split/venv \
    && echo "OK: venv symlink present" \
    || ln -s /home/faisal/EventMarketDB/venv /home/faisal/em-warmup-cache-split/venv
```

Same Python binary, same site-packages — zero functional risk.

### 6.8 Required Gates After Every Cutover (single copy-paste block)

This block is the SUPERSET of every per-stage gate from Stage 1.2 onward. Per-stage Gate sections (§Stage 1.2/2.2/3.2/5) reference this block by name and only list the stage-unique extras (verbatim-equality grep, size-shrink check, shadow-distinct check, etc.). If ANY line below exits non-zero, STOP — do not advance to next stage. **`set -euo pipefail` is mandatory** (per §0.3) — without it, a failing producer in any `| tee` / `| sort` / `| diff` / `| grep` chain is silently masked by the consumer's exit code.

```bash
set -euo pipefail
cd /home/faisal/em-warmup-cache-split
PY=/home/faisal/EventMarketDB/venv/bin/python

# Path-helper tests (PYTHONPATH=. because they import from scripts.earnings.builders directly)
PYTHONPATH=. $PY -m pytest scripts/earnings/test_builders_paths.py -q

# Identity, surface, static, warmup_cache facade tests (PYTHONPATH=scripts/earnings for bare imports)
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_imports.py -q
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_surface.py -q
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_static.py -q
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_warmup_cache.py -q

# Full builders matrix excluding live (catches everything above plus per-domain mocked units)
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_*.py -q -m "not live"

# Renderer suite — must be byte-identical (count AND test names) to baseline
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_renderer_*.py -q
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_renderer_*.py --collect-only -q | sort \
    | diff /tmp/renderer_tests_before.txt - && echo "renderer test names unchanged"

# CLI --test paths (every entry point that ends up calling _run_v2_regression_tests).
# After every cutover, diff the count against the §6.3 baseline — drift means the
# inline regression suite gained/lost check()s during the move.
PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache --test 2>&1 \
    | grep -oE '[0-9]+ passed, [0-9]+ failed out of [0-9]+' \
    | diff /tmp/warmup_split_test_count_baseline.txt - \
    && echo "--test count unchanged" \
    || { echo "FAIL: --test count drifted from baseline"; exit 1; }
$PY .claude/skills/earnings-orchestrator/scripts/warmup_cache.py --test
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh --test
```

Final live validation, ONLY after all non-live gates green and ONLY at end of Stage 5 or post-merge. **CRITICAL:** the live-mode commands need Neo4j env vars — `neograph.Neo4jConnection` reads `os.getenv("NEO4J_URI")` etc. directly and does NOT consume `.env` automatically. Source `.env` before the live block:

```bash
set -euo pipefail
cd /home/faisal/em-warmup-cache-split   # or the merged main repo post-merge
PY=/home/faisal/EventMarketDB/venv/bin/python
set -a; source .env; set +a
PYTHONPATH=. $PY -m pytest scripts/earnings/test_builders_warmup_split.py -v -m live
PYTHONPATH=scripts/earnings $PY scripts/earnings/test_builder_validation.py --ticker FIVE
PYTHONPATH=scripts/earnings $PY scripts/earnings/test_adapter_validation.py --ticker FIVE
```

If Neo4j is unreachable AND the goldens fail with a connection error (not a real diff), this is NOT a passing condition — it requires either (a) a documented external-service-outage waiver explicitly approved by the user, or (b) re-running once Neo4j is reachable. Do NOT silently treat "skip on connection error" as success.

---

## 7. Commit Ledger (10 commits total)

Stage 0 — TDD foundation (1 commit)
  0.1: Capture pre-split goldens for FIVE; add `test_builders_warmup_split.py` (skipped tests with explicit Stage-N enable comments)

Stage 1 — Extract `eight_k_packet.py` (2 commits)
  1.1 COPY: `scripts/earnings/builders/eight_k_packet.py` (verbatim move of build_8k_packet + 4 queries + _fetch_8k_core); `test_builders_eight_k_packet.py` mocked unit tests
  1.2 CUTOVER: delete moved defs from `warmup_cache.py`; add re-export block; add stand-alone `test_eight_k_packet_canonical_facade_identity` to `test_builders_imports.py` (do NOT extend EXPECTED_SURFACE / MODULE_PAIRS — see §2.3); extend `test_concurrent_imports_preserve_identity::mods_to_import`; activate Stage-1 tests in `test_builders_warmup_split.py`

Stage 2 — Extract `guidance_history.py` (2 commits)
  2.1 COPY: `scripts/earnings/builders/guidance_history.py` (verbatim move of build_guidance_history + render_guidance_text + 4 helpers + 2 queries + _SOURCE_PRIORITY + _run_v2_regression_tests); `test_builders_guidance_history.py` mocked unit tests
  2.2 CUTOVER: delete moved defs from `warmup_cache.py`; add re-export block; add stand-alone `test_guidance_history_canonical_facade_identity`; extend `test_concurrent_imports_preserve_identity::mods_to_import`; activate Stage-2 tests (no EXPECTED_SURFACE / MODULE_PAIRS edits — per §2.3)

Stage 3 — Extract `inter_quarter_context.py` (2 commits)
  3.1 COPY: `scripts/earnings/builders/inter_quarter_context.py` (verbatim move of build_inter_quarter_context + render_inter_quarter_text + ~15 helpers + 6 queries); `test_builders_inter_quarter_context.py` mocked unit tests including a stand-alone `test_parse_dt_for_pit_distinct_from_peer` for the new canonical home (the EXTENSION of the existing `test_parse_dt_for_pit_disambiguation` in `test_builders_imports.py` happens in Stage 3.2 — see detailed steps; the ledger here used to duplicate that mention but it now correctly belongs to 3.2 only)
  3.2 CUTOVER: delete moved defs from `warmup_cache.py`; add re-export block; add stand-alone `test_inter_quarter_context_canonical_facade_identity`; extend `test_parse_dt_for_pit_disambiguation` for the new canonical path; extend `test_concurrent_imports_preserve_identity::mods_to_import`; activate Stage-3 tests (no EXPECTED_SURFACE / MODULE_PAIRS edits)

Stage 4 — Adapter canonicalization (1 commit, included per user-confirmed plan choice)
  4.1: `adapters.py` lazy imports point at canonical domain modules; `test_builders_adapters.py:42` patch target updates accordingly

Stage 5 — Facade cleanup + permanent guards (1 commit)
  5.1: remove now-unused imports (`math`, `Counter`, `defaultdict`) from `warmup_cache.py`; add module-docstring update reflecting facade role; the existing `test_facade_has_no_relocated_function_defs` static check (added in Stage 0) is auto-activated by the helper gates landing in earlier stages — no new test added in Stage 5

Stage 6 — Documentation (1 commit, MANDATORY)
  6.1: `scripts/earnings/builders/README.md` — Layout table, line-count refresh, facade contract section

**Total: 1 + 2 + 2 + 2 + 1 + 1 + 1 = 10 commits.** Each commit is independently revertible with `git revert HEAD`.

---

## 8. Per-Stage Detailed Steps

### 8.0 Mid-stage rollback (if a Gate fails before commit)

If a stage's Gate fails after edits land in the worktree but BEFORE the commit, recover with:

```bash
set -euo pipefail
cd /home/faisal/em-warmup-cache-split

# Option A: discard ALL uncommitted changes in the worktree (lose every edit since last commit)
git reset --hard HEAD

# Option B: revert ONLY specific files that look wrong
git checkout HEAD -- scripts/earnings/builders/warmup_cache.py
# (repeat for each file you want to restore)

# Option C: if some edits already committed but a follow-up edit failed, revert the bad commit
git revert HEAD
```

Then re-read this stage's instructions and try again. Do NOT push, do NOT merge with a half-applied stage. The plan's invariant: every commit is self-contained and its Gate is green.

NEVER use `git checkout HEAD --` against files OUTSIDE the in-scope list (§0). NEVER use `rm -rf` on the worktree without first checking `git status` for unstaged work the user might want. When in doubt, ask.



For every stage, the structure is:

> **Goal** — one sentence
> **What changes** — file list
> **Edits** — concrete `Edit`/`Write` operations
> **Gate** — bash block that MUST exit 0
> **Commit message** — template
> **Rollback** — `git revert HEAD` (always)

### Stage 0 — TDD foundation (1 commit)

**Goal:** WRITE FAILING SPLIT-CONTRACT TESTS FIRST (TDD red phase), capture pre-split structural-equality goldens, and add the contract-test harness with stage-skipped tests so the scaffolding lands BEFORE any code move. The skipped tests ARE the local TDD red — they will turn green stage by stage as cutovers land. This stage's commit lands them in their skipped state; nothing in production behavior changes.

**Edit ordering inside this stage (do NOT reorder):**

1. Write `test_builders_warmup_split.py` into `scripts/earnings/`.
2. Capture the three FIVE goldens via the live builder commands (Step 1 of "Edits" below).
3. Strip `assembled_at` from each golden file.
4. Run the Stage 0 gate.

If you run the gate before Steps 2–3 complete, `test_fixtures_present` will fail (fixtures don't exist yet). Order is load-bearing.

**What changes:**

- NEW: `scripts/earnings/test_builders_warmup_split.py`
- NEW: `scripts/earnings/builders/test_fixtures/warmup_split/8k_packet_FIVE.json`
- NEW: `scripts/earnings/builders/test_fixtures/warmup_split/guidance_history_FIVE.json`
- NEW: `scripts/earnings/builders/test_fixtures/warmup_split/inter_quarter_context_FIVE.json`

**Edits:**

1. Inside the worktree, capture three live goldens against ticker FIVE using the verified fixture from `scripts/earnings/test_builder_validation.py:58–71` (FIVE's current 8-K accession `0001177609-25-000037`, filed `2025-08-27T16:14:48-04:00`, previous 8-K `2025-06-04T16:23:39-04:00`). DO NOT call `resolve_quarter_info('FIVE')` — the function requires TWO positional args (`ticker, accession_8k`) per `quarter_identity.py:146`. Either hard-code from the fixture (recommended for determinism) OR call `resolve_quarter_info('FIVE', ACC)` with the accession passed in.

   ```bash
   set -euo pipefail
   cd /home/faisal/em-warmup-cache-split
   PY=/home/faisal/EventMarketDB/venv/bin/python
   mkdir -p scripts/earnings/builders/test_fixtures/warmup_split

   # Hard-coded from test_builder_validation.py FIVE fixture (verified 2026-04-26):
   ACC=0001177609-25-000037
   FILED=2025-08-27T16:14:48-04:00
   PREV=2025-06-04T16:23:39-04:00

   # OPTIONAL sanity-check: confirm FIVE's quarter_info still resolves with these values
   PYTHONPATH=scripts/earnings $PY -c "
   from quarter_identity import resolve_quarter_info
   qi = resolve_quarter_info('FIVE', '$ACC')
   assert qi['filed_8k'] == '$FILED', f'filed_8k mismatch: {qi[\"filed_8k\"]} vs $FILED'
   print('quarter_info resolved OK:', qi['accession_8k'], qi['filed_8k'])
   "
   ```

   Then run the three builders. **CRITICAL:** `neograph.Neo4jConnection.get_manager()` reads `NEO4J_URI/USERNAME/PASSWORD/DATABASE` directly via `os.getenv()` — it does NOT load `.env`. The §6.7 symlink alone is insufficient. EVERY live invocation MUST source `.env` first (or set the env vars another way):

   ```bash
   set -euo pipefail
   # Source .env so neograph can read NEO4J_* vars (mirrors what warmup_cache.sh does)
   set -a; source .env; set +a

   PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache FIVE --8k-packet "$ACC" \
       --out-path scripts/earnings/builders/test_fixtures/warmup_split/8k_packet_FIVE.json
   PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache FIVE --guidance-history --pit "$FILED" \
       --out-path scripts/earnings/builders/test_fixtures/warmup_split/guidance_history_FIVE.json
   PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache FIVE --inter-quarter \
       --prev-8k "$PREV" --context-cutoff "$FILED" \
       --out-path scripts/earnings/builders/test_fixtures/warmup_split/inter_quarter_context_FIVE.json
   ```

   ALTERNATIVE (preferred for shell-script targets): use the existing `warmup_cache.sh` which already exports the Neo4j env vars from defaults, e.g.
   `bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh FIVE --8k-packet "$ACC" --out-path ...`. The skill shim's `__main__` falls through to `_impl.main()` exactly like the `python -m` invocation.

   These three files become the structural-equality goldens (compared as Python dicts after `json.loads`, modulo the stripped `assembled_at` field — NOT raw byte equality, since dict ordering on disk depends on the JSON encoder's settings). Strip the volatile `assembled_at` field before commit (the harness ignores it on comparison):

   ```bash
   set -euo pipefail
   for f in scripts/earnings/builders/test_fixtures/warmup_split/*.json; do
       $PY -c "
   import json,sys
   p=sys.argv[1]
   with open(p) as fh: d=json.load(fh)
   d.pop('assembled_at', None)
   with open(p,'w') as fh: json.dump(d, fh, indent=2, default=str, ensure_ascii=False, sort_keys=True)
   " "$f"
   done
   ```

   If FIVE doesn't have meaningful guidance data, the captured golden is the empty-packet shape (`{"schema_version": "guidance_history.v1", "ticker": "FIVE", "series": [], "summary": {"total_series": 0, ...}, ...}`). The empty-packet shape IS the contract worth pinning — Stage 5's structural-equality test confirms an empty FIVE post-split is still byte-identical to an empty FIVE pre-split. Same logic for empty IQ events.

   **Required action after capture:** open each fixture JSON manually and confirm `schema_version` is present. If a fixture is structurally invalid (e.g., the builder threw and wrote nothing or partial output), STOP — pick a fallback ticker (`MMM`, `AAPL`, or `CRM` — all have known stable guidance and IQ history) and re-capture all three goldens against that ticker. Update every test file reference (`test_builders_warmup_split.py` constants like `TICKER` and the `golden["accession_8k"]` reads) to match. Do NOT proceed with broken goldens.

2. Write `scripts/earnings/test_builders_warmup_split.py`:

   ```python
   """Contract harness for the warmup_cache → 3-domain split.

   Pre-split goldens captured in Stage 0 are compared against post-split
   builder output to prove structural equality (Python dict `==` after `json.loads`,
   modulo the stripped `assembled_at` field — NOT raw byte equality, since on-disk
   JSON byte order depends on the encoder's settings).

   Identity tests prove that every relocated symbol resolves to the SAME
   Python object via `is` from BOTH the warmup_cache facade AND the canonical
   domain module.

   Tests are gated by intrinsic stage state (no marker file) so they activate
   as the split progresses:
     - Stage-0 tests: harness loads, fixtures present, no-back-import static check
     - Stage-1.2 tests: skip until eight_k_packet.py exists, then activate
     - Stage-2.2 tests: skip until guidance_history.py exists, then activate
     - Stage-3.2 tests: skip until inter_quarter_context.py exists, then activate
     - Stage-5 tests: no-redefine assertion gated on `_all_reexport_blocks_present()` (activates at Stage 3.2 cutover, fails loudly on regression — does NOT self-disable on def re-introduction); size assertion + goldens gated on `_all_cutovers_complete()`
   """
   from __future__ import annotations
   import ast
   import json
   import os
   import subprocess
   import sys
   from pathlib import Path
   import pytest

   REPO = Path(__file__).resolve().parents[2]
   PY = sys.executable
   FIXTURES = REPO / "scripts/earnings/builders/test_fixtures/warmup_split"
   WC_PATH = REPO / "scripts/earnings/builders/warmup_cache.py"

   pytestmark = pytest.mark.builders


   # ── Cutover-detection helpers (shared by every stage-gated test) ────────
   #
   # CRITICAL: these are SKIP gates only. They detect whether a stage has happened
   # yet — they do NOT replace the actual assertions. The assertion side of each
   # gated test must FAIL loudly when the contract is violated, not silently skip.

   import re

   def _wc_still_defines(sym: str) -> bool:
       """True iff warmup_cache.py still contains `def {sym}(` or `{sym} = ` at column 0.
       Used to skip facade-vs-canonical identity tests during COPY-only stages where
       both modules legitimately have their own def (different objects by design)."""
       if not WC_PATH.exists():
           return False
       src = WC_PATH.read_text()
       return bool(re.search(rf'^def {re.escape(sym)}\(|^{re.escape(sym)} = ',
                             src, re.MULTILINE))

   def _domain_modules_exist() -> bool:
       """Skip-gate: all 3 domain modules created (Stages 1.1, 2.1, 3.1 done)."""
       builders = REPO / "scripts/earnings/builders"
       return all((builders / f"{m}.py").exists()
                  for m in ("eight_k_packet", "guidance_history", "inter_quarter_context"))

   def _all_cutovers_complete() -> bool:
       """Skip-gate: all 3 build_* defs REMOVED from warmup_cache.py (Stages 1.2/2.2/3.2 done).
       The static-no-redefine ASSERTION is separate (test_facade_has_no_relocated_function_defs)
       — it MUST fail loudly if a def reappears, not silently skip."""
       if not _domain_modules_exist() or not WC_PATH.exists():
           return False
       src = WC_PATH.read_text()
       return not any(f"def {fn}(" in src for fn in
                      ("build_8k_packet", "build_guidance_history", "build_inter_quarter_context"))

   def _all_reexport_blocks_present() -> bool:
       """Skip-gate for the static no-redefine assertion. Detects "all 3 cutover commits
       have landed" by checking warmup_cache.py contains all 3 `from .X import` re-export
       blocks. Independent of whether someone later re-introduces a def — so it does NOT
       self-disable on regression. Use this for test_facade_has_no_relocated_function_defs;
       use _all_cutovers_complete() (which DOES short-circuit on def-presence) for skip-gates
       where the test is verifying byte-output (goldens) rather than absence-of-def."""
       if not WC_PATH.exists():
           return False
       src = WC_PATH.read_text()
       return all(f"from .{m} import" in src for m in
                  ("eight_k_packet", "guidance_history", "inter_quarter_context"))


   # ── Stage 0: harness sanity ─────────────────────────────────────────────

   def test_fixtures_present():
       assert (FIXTURES / "8k_packet_FIVE.json").exists()
       assert (FIXTURES / "guidance_history_FIVE.json").exists()
       assert (FIXTURES / "inter_quarter_context_FIVE.json").exists()


   def test_no_warmup_cache_back_imports():
       """The new domain modules MUST NOT import warmup_cache (cycle prevention).

       Catches:
         - `import warmup_cache` (and `import warmup_cache as wc`)
         - `from warmup_cache import X`
         - `from .warmup_cache import X`
         - `from scripts.earnings.builders.warmup_cache import X`
         - `from . import warmup_cache` (alias-style)
         - `from scripts.earnings.builders import warmup_cache` (alias-style)
       """
       targets = [
           REPO / "scripts/earnings/builders/eight_k_packet.py",
           REPO / "scripts/earnings/builders/guidance_history.py",
           REPO / "scripts/earnings/builders/inter_quarter_context.py",
       ]
       any_present = False
       for path in targets:
           if not path.exists():
               continue
           any_present = True
           tree = ast.parse(path.read_text())
           for node in ast.walk(tree):
               if isinstance(node, ast.ImportFrom):
                   if node.module and "warmup_cache" in node.module:
                       pytest.fail(
                           f"{path.name}: ImportFrom module references warmup_cache "
                           f"({node.module}) — cycle"
                       )
                   # ALSO check the names imported (`from . import warmup_cache`)
                   for alias in node.names:
                       if "warmup_cache" in alias.name:
                           pytest.fail(
                               f"{path.name}: ImportFrom imports name 'warmup_cache' "
                               f"(from {node.module or '.'} import {alias.name}) — cycle"
                           )
               if isinstance(node, ast.Import):
                   for n in node.names:
                       if "warmup_cache" in n.name:
                           pytest.fail(
                               f"{path.name}: import statement references warmup_cache "
                               f"({n.name}) — cycle"
                           )
       if not any_present:
           pytest.skip("no domain modules exist yet (pre-Stage-1.1)")


   def test_no_cross_domain_imports():
       """The 3 domain modules MUST be PEERS — none imports another. Cross-imports
       create silent coupling that bypasses the facade-only contract. See §10.18.

       Catches `from .guidance_history import _format_value` placed in
       inter_quarter_context.py (or any analogous cross-coupling), AND alias-style
       `from . import guidance_history`."""
       targets = ["eight_k_packet", "guidance_history", "inter_quarter_context"]
       any_present = False
       for me in targets:
           path = REPO / f"scripts/earnings/builders/{me}.py"
           if not path.exists():
               continue
           any_present = True
           tree = ast.parse(path.read_text())
           for node in ast.walk(tree):
               if isinstance(node, ast.ImportFrom):
                   if node.module:
                       for other in targets:
                           if other != me and other in node.module:
                               pytest.fail(
                                   f"{me}.py imports from {node.module} — domain "
                                   f"modules must be peers; share via the warmup_cache "
                                   f"facade only"
                               )
                   for alias in node.names:
                       for other in targets:
                           if other != me and alias.name == other:
                               pytest.fail(
                                   f"{me}.py: ImportFrom imports '{alias.name}' "
                                   f"(from {node.module or '.'}) — domain modules "
                                   f"must be peers"
                               )
       if not any_present:
           pytest.skip("no domain modules exist yet (pre-Stage-1.1)")


   # ── Stage 1.2: eight_k_packet identity + golden ─────────────────────────

   _EIGHTK_SYMBOLS = [
       "build_8k_packet", "_fetch_8k_core",
       "QUERY_4J", "QUERY_4K", "QUERY_4G_META", "QUERY_4K_OTHER_PREVIEW", "QUERY_4F",
   ]

   @pytest.mark.parametrize("sym", _EIGHTK_SYMBOLS)
   def test_facade_reexports_match_eight_k_packet_canonical(sym):
       try:
           from scripts.earnings.builders import eight_k_packet as ek
       except ImportError:
           pytest.skip("eight_k_packet not yet created (pre-Stage-1.1)")
       # CRITICAL CUTOVER GATE: in Stage 1.1 (COPY-only), warmup_cache still has its
       # own `def build_8k_packet` etc. Both modules legitimately have their own
       # def — they're different objects BY DESIGN. The identity assertion only
       # makes sense AFTER Stage 1.2 cutover removes warmup_cache's local def.
       if _wc_still_defines(sym):
           pytest.skip(f"warmup_cache.py still defines {sym} — pre-Stage-1.2 cutover")
       from scripts.earnings.builders import warmup_cache as wc
       facade = getattr(wc, sym, None)
       canonical = getattr(ek, sym, None)
       if canonical is None:
           pytest.skip(f"{sym} not yet in eight_k_packet (pre-Stage-1.1)")
       if facade is None:
           pytest.fail(
               f"warmup_cache.{sym} missing — facade must re-export every "
               f"relocated symbol (Stage 1.2 must add the import block)"
           )
       assert facade is canonical, (
           f"IDENTITY BROKEN: warmup_cache.{sym} ({id(facade)}) is not "
           f"eight_k_packet.{sym} ({id(canonical)}) — facade must use direct "
           f"`from .eight_k_packet import {sym}`, NOT a wrapper function"
       )


   # ── Stage 2.2: guidance_history identity ────────────────────────────────

   _GUIDANCE_SYMBOLS = [
       "build_guidance_history", "render_guidance_text", "resolve_unit_groups",
       "_format_value", "_extract_given_day", "_normalize_qualitative",
       "_SOURCE_PRIORITY",
       "QUERY_GUIDANCE_HISTORY", "QUERY_GUIDANCE_HISTORY_PIT",
       "_run_v2_regression_tests",
   ]

   @pytest.mark.parametrize("sym", _GUIDANCE_SYMBOLS)
   def test_facade_reexports_match_guidance_history_canonical(sym):
       try:
           from scripts.earnings.builders import guidance_history as gh
       except ImportError:
           pytest.skip("guidance_history not yet created (pre-Stage-2.1)")
       if _wc_still_defines(sym):
           pytest.skip(f"warmup_cache.py still defines {sym} — pre-Stage-2.2 cutover")
       from scripts.earnings.builders import warmup_cache as wc
       facade = getattr(wc, sym, None)
       canonical = getattr(gh, sym, None)
       if canonical is None:
           pytest.skip(f"{sym} not yet in guidance_history (pre-Stage-2.1)")
       if facade is None:
           pytest.fail(f"warmup_cache.{sym} missing after Stage 2.2 cutover")
       assert facade is canonical, (
           f"IDENTITY BROKEN: warmup_cache.{sym} is not guidance_history.{sym}"
       )


   # ── Stage 3.2: inter_quarter_context identity ───────────────────────────

   _IQ_SYMBOLS = [
       "build_inter_quarter_context", "render_inter_quarter_text",
       "_parse_dt_for_pit", "_is_price_pit_safe", "_build_forward_returns",
       "_iq_parse_json_field", "_norm_ret", "_fmt_vol", "_fmt_txn",
       "_safe_adj", "_event_ref", "_day_from_ts",
       "_cutoff_boundary_price_role", "_best_safe_horizon", "_report_summary",
       "_render_window_label_news", "_render_window_label_filing",
       "_render_horizon_line_filing", "_render_news_react_line",
       "QUERY_IQ_PRICES", "QUERY_IQ_NEWS", "QUERY_IQ_FILINGS",
       "QUERY_IQ_DIVIDENDS", "QUERY_IQ_SPLITS", "QUERY_IQ_COMPANY_CONTEXT",
   ]

   @pytest.mark.parametrize("sym", _IQ_SYMBOLS)
   def test_facade_reexports_match_inter_quarter_context_canonical(sym):
       try:
           from scripts.earnings.builders import inter_quarter_context as iq
       except ImportError:
           pytest.skip("inter_quarter_context not yet created (pre-Stage-3.1)")
       if _wc_still_defines(sym):
           pytest.skip(f"warmup_cache.py still defines {sym} — pre-Stage-3.2 cutover")
       from scripts.earnings.builders import warmup_cache as wc
       facade = getattr(wc, sym, None)
       canonical = getattr(iq, sym, None)
       if canonical is None:
           pytest.skip(f"{sym} not yet in inter_quarter_context (pre-Stage-3.1)")
       if facade is None:
           pytest.fail(f"warmup_cache.{sym} missing after Stage 3.2 cutover")
       assert facade is canonical, (
           f"IDENTITY BROKEN: warmup_cache.{sym} is not inter_quarter_context.{sym}"
       )


   # NOTE: Stage 5 gating now uses TWO different helpers depending on the assertion's
   # purpose:
   #   - `_all_reexport_blocks_present()` for the no-redefine guard. Activates at
   #     Stage 3.2 cutover (when all 3 `from .X import` blocks land in warmup_cache.py)
   #     and KEEPS firing on regression (re-export blocks remain even if a stray def
   #     is added back), so the assertion fails LOUDLY on def re-introduction.
   #   - `_all_cutovers_complete()` for the facade-size assertion + live goldens
   #     (these tests need the absence-of-build_*-defs as a real precondition).
   # We previously had a single helper `_stage5_complete()` that combined skip-gate +
   # assertion logic — but if it returned False because someone re-introduced a
   # relocated def, the test SKIPPED instead of FAILING, masking the regression.
   # Splitting + choosing the right gate per test fixes the self-disable.

   # ── Stage 5: facade has NO relocated `def` blocks ───────────────────────

   _RELOCATED_FUNCTIONS = {
       "build_8k_packet", "build_guidance_history", "build_inter_quarter_context",
       "render_guidance_text", "render_inter_quarter_text",
       "_fetch_8k_core",
       "_format_value", "resolve_unit_groups", "_extract_given_day",
       "_normalize_qualitative", "_run_v2_regression_tests",
       "_parse_dt_for_pit", "_is_price_pit_safe", "_build_forward_returns",
       "_iq_parse_json_field", "_norm_ret", "_fmt_vol", "_fmt_txn",
       "_safe_adj", "_event_ref", "_day_from_ts",
       "_cutoff_boundary_price_role", "_best_safe_horizon", "_report_summary",
       "_render_window_label_news", "_render_window_label_filing",
       "_render_horizon_line_filing", "_render_news_react_line",
   }

   def test_facade_has_no_relocated_function_defs():
       """STAGE 3.2+ ASSERT (loud-fail): warmup_cache.py contains NO `def` for any relocated
       symbol — the facade's surface for these names comes from re-exports only.

       Skip-gate: `_all_reexport_blocks_present()` — TRUE only when all 3 cutover commits
       have landed (re-export blocks present in warmup_cache.py). CRITICAL: this gate must
       NOT use `_domain_modules_exist()` (true after Stage 3.1 COPY, BEFORE Stage 3.2 cutover
       removes the IQ defs — the test would FAIL spuriously during Stage 3.1's full matrix).
       It must NOT use `_all_cutovers_complete()` either (that one short-circuits on
       def-presence — would cause the test to silently SKIP if a maintainer re-introduces
       a def post-Stage-5, masking the regression).

       The chosen gate fires from Stage 3.2 onward AND keeps firing if a def reappears
       (re-export blocks remain even when a stray def is added back), so the assertion
       fails loudly on regression."""
       if not _all_reexport_blocks_present():
           pytest.skip("not all 3 re-export blocks present yet — pre-Stage-3.2 cutover")
       tree = ast.parse(WC_PATH.read_text())
       redefined = [
           n.name for n in ast.walk(tree)
           if isinstance(n, ast.FunctionDef) and n.name in _RELOCATED_FUNCTIONS
       ]
       assert not redefined, (
           f"warmup_cache.py redefines relocated functions: {redefined} — "
           f"these must come from re-export only after Stage 5"
       )


   def test_facade_size_after_cleanup():
       """STAGE 5 ASSERT (loud-fail): after import cleanup + def-removal, warmup_cache.py
       is < 800 lines (baseline 2066, target ~520). Skips until cutovers complete."""
       if not _all_cutovers_complete():
           pytest.skip("cutovers not complete — pre-Stage-3.2")
       lines = len(WC_PATH.read_text().splitlines())
       assert lines < 800, (
           f"warmup_cache.py is {lines} lines after cleanup — expected < 800 (target ~520). "
           f"Some relocated content may not have been actually removed."
       )


   # ── Stage 5: golden structural-equality (post-split) ─────────────────────────

   def _strip_volatile(d: dict) -> dict:
       d = dict(d)
       d.pop("assembled_at", None)
       return d


   @pytest.mark.live
   def test_golden_8k_packet_FIVE_byte_equal_post_split():
       if not _all_cutovers_complete():
           pytest.skip("cutovers not complete — goldens only meaningful post-Stage-3.2")
       golden = json.loads((FIXTURES / "8k_packet_FIVE.json").read_text())
       acc = golden["accession_8k"]
       out = "/tmp/post_split_8k_FIVE.json"
       subprocess.run(
           [PY, "-m", "scripts.earnings.builders.warmup_cache",
            "FIVE", "--8k-packet", acc, "--out-path", out],
           check=True, env={**os.environ, "PYTHONPATH": str(REPO)},
       )
       actual = _strip_volatile(json.loads(Path(out).read_text()))
       assert actual == golden, "8k_packet golden mismatch — schema or behavior drift"


   @pytest.mark.live
   def test_golden_guidance_history_FIVE_byte_equal_post_split():
       if not _all_cutovers_complete():
           pytest.skip("cutovers not complete — goldens only meaningful post-Stage-3.2")
       golden = json.loads((FIXTURES / "guidance_history_FIVE.json").read_text())
       pit = golden.get("pit") or "<set-from-golden-or-skip>"
       if pit == "<set-from-golden-or-skip>":
           pytest.skip("golden has no pit — re-capture during Stage 0")
       out = "/tmp/post_split_guidance_FIVE.json"
       subprocess.run(
           [PY, "-m", "scripts.earnings.builders.warmup_cache",
            "FIVE", "--guidance-history", "--pit", pit, "--out-path", out],
           check=True, env={**os.environ, "PYTHONPATH": str(REPO)},
       )
       actual = _strip_volatile(json.loads(Path(out).read_text()))
       assert actual == golden, "guidance_history golden mismatch"


   @pytest.mark.live
   def test_golden_inter_quarter_FIVE_byte_equal_post_split():
       if not _all_cutovers_complete():
           pytest.skip("cutovers not complete — goldens only meaningful post-Stage-3.2")
       golden = json.loads((FIXTURES / "inter_quarter_context_FIVE.json").read_text())
       prev = golden["prev_8k_ts"]
       cutoff = golden["context_cutoff_ts"]
       out = "/tmp/post_split_iq_FIVE.json"
       subprocess.run(
           [PY, "-m", "scripts.earnings.builders.warmup_cache",
            "FIVE", "--inter-quarter", "--prev-8k", prev,
            "--context-cutoff", cutoff, "--out-path", out],
           check=True, env={**os.environ, "PYTHONPATH": str(REPO)},
       )
       actual = _strip_volatile(json.loads(Path(out).read_text()))
       assert actual == golden, "inter_quarter_context golden mismatch"
   ```

3. Verify the test file collects without errors:

   ```bash
   cd /home/faisal/em-warmup-cache-split
   PYTHONPATH=scripts/earnings /home/faisal/EventMarketDB/venv/bin/python \
       -m pytest scripts/earnings/test_builders_warmup_split.py --collect-only -q
   # expect: tests collected, several skipped (because domain modules not yet created)
   ```

**Gate (Stage 0):**

```bash
set -euo pipefail
cd /home/faisal/em-warmup-cache-split
PY=/home/faisal/EventMarketDB/venv/bin/python

# Baseline still green (no production code changed)
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_*.py -q -m "not live"
# expect: same as pre-flight (165 passed) + new test file's stage-0-active tests
# The new test_builders_warmup_split.py contributes:
#   - test_fixtures_present: PASS
#   - test_no_warmup_cache_back_imports: PASS (skipped — no domain modules yet)
#   - test_facade_reexports_match_*: PASS (skipped — domain modules absent)
#   - test_no_cross_domain_imports: PASS (skipped — no domain modules yet)
#   - test_facade_has_no_relocated_function_defs: PASS (skipped — _all_reexport_blocks_present() == False pre-Stage-3.2)
#   - test_facade_size_after_cleanup: PASS (skipped — _all_cutovers_complete() == False pre-Stage-3.2)
#   - test_golden_*: PASS (skipped — _all_cutovers_complete() == False; also @pytest.mark.live)

# Fixture files are valid JSON
$PY -c "
import json, glob
for p in glob.glob('scripts/earnings/builders/test_fixtures/warmup_split/*.json'):
    d = json.loads(open(p).read())
    assert 'schema_version' in d, p
    assert 'assembled_at' not in d, f'{p} contains assembled_at — must strip before commit'
    print(p, d['schema_version'])
"
```

**Commit message:**

```
test(builders): TDD foundation for warmup_cache 3-way split (commit 1/10)

- Capture pre-split FIVE goldens for 8k_packet, guidance_history,
  inter_quarter_context (assembled_at stripped) — these become structural-equality
  pins for Stage 5.
- Add scripts/earnings/test_builders_warmup_split.py — contract harness with:
  - fixture sanity check
  - no-back-imports static check (skips until domain modules exist)
  - per-domain facade-vs-canonical identity tests (skipped per stage)
  - Stage-5 static check for no redefined functions in warmup_cache
  - Stage-5 golden structural-equality (live, auto-activates via _all_cutovers_complete() intrinsic check)

Pure TDD additive — no production code touched.
```

**Rollback:** `git revert HEAD`.

---

### Stage 1 — Extract `eight_k_packet.py` (2 commits)

#### Stage 1.1 COPY — additive, both copies coexist

**Goal:** create the canonical eight_k_packet module with verbatim copies of all moving symbols + mocked unit tests. `warmup_cache.py` is UNCHANGED in this commit (defs still live there too).

**What changes:**

- NEW: `scripts/earnings/builders/eight_k_packet.py`
- NEW: `scripts/earnings/test_builders_eight_k_packet.py`

**Edits:**

1. Write `scripts/earnings/builders/eight_k_packet.py`:

   ```python
   #!/usr/bin/env python3
   """8-K packet builder — orchestration side.

   Owns:
     - QUERY_4J, QUERY_4K       (8-K sections + EX-99 exhibits)
     - QUERY_4G_META            (8-K metadata + inventory)
     - QUERY_4K_OTHER_PREVIEW   (non-99 exhibit previews)
     - QUERY_4F                 (filing text fallback)
     - _fetch_8k_core(manager, accession) -> (sections, exhibits_99)
     - build_8k_packet(accession, ticker, out_path=None) -> packet dict

   Re-exported from scripts.earnings.builders.warmup_cache for back-compat —
   adapters, tests, and the .claude skill shim continue to import from
   warmup_cache without change.

   ─────────────────────────────────────────────────────────────────────
   SHARED OWNERSHIP WARNING

   _fetch_8k_core() is shared by:
     - warmup_cache.run_8k()       — extraction CLI mode (--8k)
     - build_8k_packet()           — earnings orchestration

   warmup_cache.run_8k accesses _fetch_8k_core via the warmup_cache facade
   re-export, so identity is preserved across both call sites. Changing
   _fetch_8k_core() affects BOTH pipelines.
   ─────────────────────────────────────────────────────────────────────
   """
   from __future__ import annotations

   import json
   import os
   from datetime import datetime, timezone

   from ._paths import ensure_legacy_paths
   ensure_legacy_paths()

   from neograph.Neo4jConnection import get_manager


   # ── Cypher queries (verbatim from warmup_cache.py @ 258-313) ──────────
   QUERY_4J = """ ... """  # (verbatim from warmup_cache.py:258-262)
   QUERY_4K = """ ... """  # (verbatim from warmup_cache.py:264-269)
   QUERY_4G_META = """ ... """  # (verbatim from warmup_cache.py:275-293)
   QUERY_4K_OTHER_PREVIEW = """ ... """  # (verbatim from warmup_cache.py:298-305)
   QUERY_4F = """ ... """  # (verbatim from warmup_cache.py:310-313)


   def _fetch_8k_core(manager, accession):
       """Private helper: run 4J + 4K queries, return (sections, exhibits_99).

       Shared by warmup_cache.run_8k() and build_8k_packet() (this module).
       """
       # (verbatim body from warmup_cache.py:433-440)


   def build_8k_packet(accession, ticker, out_path=None):
       """Assemble canonical 8k_packet.v1 for earnings orchestration.

       Steps: 4G metadata → _fetch_8k_core() → non-99 exhibits → filing text
       fallback → assemble → atomic write.
       Returns: packet dict (8k_packet.v1).
       """
       # (verbatim body from warmup_cache.py:466-562)
   ```

   **CRITICAL:** Each `"""..."""` MUST contain the verbatim Cypher string from `warmup_cache.py` — not a paraphrase. Each function body MUST be byte-identical to the original. Use Read+Write, not paraphrase. The `Edit` tool's exact-match contract makes this safe — copy each block as a single string.

2. Write `scripts/earnings/test_builders_eight_k_packet.py`:

   ```python
   """Mocked unit tests for eight_k_packet (Stage 1.1)."""
   from __future__ import annotations
   import json
   import os
   from unittest.mock import MagicMock, patch
   import pytest

   from scripts.earnings.builders import eight_k_packet as ek

   pytestmark = pytest.mark.builders


   def _mock_manager(rows_by_query):
       """Mock Neo4j manager that routes queries by EXACT identity match against the
       canonical query-constant strings imported from `eight_k_packet`.

       CRITICAL: substring routing is fragile and misroutes queries here. Specifically,
       `QUERY_4G_META` contains both `'PRIMARY_FILER'` AND `'ExtractedSectionContent'`
       AND `'section_name'`, so a substring router that gates on those tokens would
       misclassify 4G as 4J or vice-versa. Exact-equality routing against the imported
       constants eliminates this risk and stays correct if the Cypher bodies evolve."""
       m = MagicMock()
       def execute(query, params):
           if query == ek.QUERY_4G_META:
               return rows_by_query.get("4G_META", [])
           if query == ek.QUERY_4J:
               return rows_by_query.get("4J", [])
           if query == ek.QUERY_4K:
               return rows_by_query.get("4K", [])
           if query == ek.QUERY_4K_OTHER_PREVIEW:
               return rows_by_query.get("4K_OTHER", [])
           if query == ek.QUERY_4F:
               return rows_by_query.get("4F", [])
           raise AssertionError(f"unexpected query: {query[:120]}")
       m.execute_cypher_query_all.side_effect = execute
       m.close = MagicMock()
       return m


   @pytest.fixture
   def base_meta():
       return {
           "filed_8k": "2024-09-15T16:00:00-04:00",
           "form_type": "8-K",
           "items": '["Item 2.02", "Item 9.01"]',
           "period_of_report": "2024-09-15",
           "market_session": "post_market",
           "is_amendment": False,
           "cik": 12345,
           "sector": "Technology",
           "exhibit_numbers": ["EX-99.1", "EX-99.2", "EX-101"],
           "section_names": ["Item2.02ResultsofOperationsandFinancialCondition"],
           "has_filing_text": True,
       }


   def test_no_metadata_raises_value_error(tmp_path, base_meta):
       mgr = _mock_manager({"4G_META": []})
       with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
           out = str(tmp_path / "out.json")
           with pytest.raises(ValueError, match="No Report found"):
               ek.build_8k_packet("0000000000-00-000000", "FAKE", out_path=out)
       mgr.close.assert_called_once()


   def test_items_json_string_parsed(tmp_path, base_meta):
       mgr = _mock_manager({
           "4G_META": [base_meta],
           "4J": [], "4K": [], "4K_OTHER": [], "4F": [],
       })
       with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
           out = str(tmp_path / "out.json")
           packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
       assert packet["items"] == ["Item 2.02", "Item 9.01"]


   def test_items_invalid_json_falls_back_to_single(tmp_path, base_meta):
       base_meta["items"] = "not-json-actually"
       mgr = _mock_manager({
           "4G_META": [base_meta],
           "4J": [], "4K": [], "4K_OTHER": [], "4F": [],
       })
       with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
           out = str(tmp_path / "out.json")
           packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
       assert packet["items"] == ["not-json-actually"]


   def test_null_stripping_in_inventory(tmp_path, base_meta):
       base_meta["section_names"] = [None, "RealSection", None]
       base_meta["exhibit_numbers"] = ["EX-99.1", None]
       mgr = _mock_manager({
           "4G_META": [base_meta],
           "4J": [], "4K": [], "4K_OTHER": [], "4F": [],
       })
       with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
           out = str(tmp_path / "out.json")
           packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
       assert packet["content_inventory"]["section_names"] == ["RealSection"]
       assert packet["content_inventory"]["exhibit_numbers"] == ["EX-99.1"]


   def test_other_exhibit_preview_only_when_diff(tmp_path, base_meta):
       # inventory says EX-99.1, EX-99.2, EX-101 — _fetch_8k_core returns 99.1+99.2
       # — so EX-101 is the "other" that needs preview
       mgr = _mock_manager({
           "4G_META": [base_meta],
           "4J": [],
           "4K": [{"exhibit_number": "EX-99.1", "content": "ex99-content"},
                  {"exhibit_number": "EX-99.2", "content": "ex99-other"}],
           "4K_OTHER": [{"exhibit_number": "EX-101",
                         "content_preview": "preview...", "full_size": 12345}],
           "4F": [],
       })
       with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
           out = str(tmp_path / "out.json")
           packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
       assert len(packet["exhibits_other"]) == 1
       assert packet["exhibits_other"][0]["exhibit_number"] == "EX-101"


   def test_filing_text_fallback_when_all_empty(tmp_path, base_meta):
       base_meta["section_names"] = []
       base_meta["exhibit_numbers"] = []
       mgr = _mock_manager({
           "4G_META": [base_meta],
           "4J": [], "4K": [], "4K_OTHER": [],
           "4F": [{"content": "fallback-text-content"}],
       })
       with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
           out = str(tmp_path / "out.json")
           packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
       assert packet["filing_text"] == "fallback-text-content"


   def test_atomic_write_default_path(tmp_path, base_meta):
       mgr = _mock_manager({
           "4G_META": [base_meta],
           "4J": [], "4K": [], "4K_OTHER": [], "4F": [],
       })
       with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
           # Use explicit tmp_path to avoid touching /tmp
           out = str(tmp_path / "out.json")
           packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
       assert os.path.exists(out)
       on_disk = json.load(open(out))
       assert on_disk["accession_8k"] == "ACC"


   def test_manager_close_on_exception(tmp_path):
       mgr = MagicMock()
       mgr.execute_cypher_query_all.side_effect = RuntimeError("kaboom")
       mgr.close = MagicMock()
       with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
           with pytest.raises(RuntimeError, match="kaboom"):
               ek.build_8k_packet("ACC", "FAKE", out_path=str(tmp_path / "x.json"))
       mgr.close.assert_called_once()


   def test_items_already_a_list_passes_through(tmp_path, base_meta):
       """When meta.items is already a Python list (not a JSON string), it must
       pass through unchanged."""
       base_meta["items"] = ["Item 7.01"]
       mgr = _mock_manager({
           "4G_META": [base_meta],
           "4J": [], "4K": [], "4K_OTHER": [], "4F": [],
       })
       with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
           out = str(tmp_path / "out.json")
           packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
       assert packet["items"] == ["Item 7.01"]


   def test_no_other_exhibit_preview_when_no_diff(tmp_path, base_meta):
       """When 4G inventory matches the EX-99 set exactly (no non-99 leftover),
       4K_OTHER_PREVIEW must NOT be queried — packet['exhibits_other'] is empty.
       Guards the inventory-diff condition that saves a Cypher round-trip."""
       base_meta["exhibit_numbers"] = ["EX-99.1"]
       mgr = _mock_manager({
           "4G_META": [base_meta],
           "4J": [],
           "4K": [{"exhibit_number": "EX-99.1", "content": "x"}],
           "4K_OTHER": [],  # MUST not be queried; empty answer is the safety net
           "4F": [],
       })
       with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
           out = str(tmp_path / "out.json")
           packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
       assert packet["exhibits_other"] == []


   def test_filing_text_NOT_fetched_when_structured_content_present(tmp_path, base_meta):
       """Inverse of test_filing_text_fallback_when_all_empty — if ANY of
       (sections, ex99, exhibits_other) is non-empty, 4F must NOT be queried
       and packet['filing_text'] must be None. Guards the fallback predicate."""
       mgr = _mock_manager({
           "4G_META": [base_meta],
           "4J": [{"section_name": "Item2.02", "content": "real-section"}],
           "4K": [], "4K_OTHER": [],
           "4F": [{"content": "WHO_QUERIED_ME"}],  # if this appears, the predicate is wrong
       })
       with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
           out = str(tmp_path / "out.json")
           packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
       assert packet["filing_text"] is None


   # NOTE: `test_run_8k_uses_canonical_fetch_8k_core` is INTENTIONALLY ABSENT from
   # Stage 1.1 — it cannot pass during COPY-only stages because both modules legitimately
   # have their own def. It is added in Stage 1.2 (CUTOVER) — see Stage 1.2 step 8 below.
   ```

**Gate (Stage 1.1):**

```bash
set -euo pipefail
cd /home/faisal/em-warmup-cache-split
PY=/home/faisal/EventMarketDB/venv/bin/python

# 1. New file compiles
$PY -m py_compile scripts/earnings/builders/eight_k_packet.py
# expect: silent

# 2. New module imports
PYTHONPATH=. $PY -c "
from scripts.earnings.builders import eight_k_packet as ek
for sym in ['build_8k_packet', '_fetch_8k_core', 'QUERY_4J', 'QUERY_4K',
            'QUERY_4G_META', 'QUERY_4K_OTHER_PREVIEW', 'QUERY_4F']:
    assert hasattr(ek, sym), f'missing {sym}'
print('OK')
"
# expect: OK

# 3. New mocked tests pass — exit code 0 is the gate; do NOT lock to a specific count
#    (count drifts as tests are added/removed; locking creates flaky-on-add false positives).
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_eight_k_packet.py -v
# expect: exit code 0 (currently ~11 tests after the missing-bullet additions; capture exact
#         number once for your records, but do NOT hard-code into the gate)

# 4. Verbatim-equality of the moved code AND query constants. Functions compared via
#    ast.dump(annotate_fields=False) (stable across Python minor versions); query constants
#    compared via raw string equality. ast.unparse() is unstable across 3.8/3.9/3.10/3.11/3.12
#    (whitespace, quote style, paren insertion all differ); ast.dump is the canonical check.
#    Query constants must match byte-exact because the mocked test router routes by exact
#    string equality (see _mock_manager) — a stray space or escaped char silently misroutes.
$PY -c "
import ast, pathlib
old = ast.parse(pathlib.Path('scripts/earnings/builders/warmup_cache.py').read_text())
new = ast.parse(pathlib.Path('scripts/earnings/builders/eight_k_packet.py').read_text())

def get_func(tree, name):
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    return None

def get_const(tree, name):
    '''Return the string literal assigned at module level to NAME, or None.'''
    for n in ast.walk(tree):
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name
                and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)):
            return n.value.value
    return None

for fn in ['build_8k_packet', '_fetch_8k_core']:
    o, n = get_func(old, fn), get_func(new, fn)
    assert o is not None and n is not None, f'{fn} missing in one of the two trees'
    o_dump = ast.dump(o, annotate_fields=False, include_attributes=False)
    n_dump = ast.dump(n, annotate_fields=False, include_attributes=False)
    assert o_dump == n_dump, f'{fn} AST differs — copy must be verbatim'

for q in ['QUERY_4J', 'QUERY_4K', 'QUERY_4G_META', 'QUERY_4K_OTHER_PREVIEW', 'QUERY_4F']:
    o, n = get_const(old, q), get_const(new, q)
    assert o is not None, f'{q} missing in warmup_cache.py'
    assert n is not None, f'{q} missing in eight_k_packet.py'
    assert o == n, f'{q} string body differs — copy must be byte-identical'

print('verbatim OK (2 functions + 5 queries)')
"
# expect: verbatim OK (2 functions + 5 queries)

# 5. Existing test suite still green (defs in BOTH places; no caller updated yet)
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_*.py -q -m "not live"
# expect: 165 passed + 8 new (=173) — NOTHING regressed

# 6. CLI --test still passes
PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache --test
# expect: same exit code, same output
PYTHONPATH=scripts/earnings $PY .claude/skills/earnings-orchestrator/scripts/warmup_cache.py --test
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh --test
# expect: all pass
```

**Commit message (1.1):**

```
refactor(builders): copy 8-K packet symbols into eight_k_packet.py (commit 2/10)

Additive copy — defs still live in warmup_cache.py too. The cutover happens
in commit 3/10. Identity invariant intentionally not yet tested (two distinct
function objects until cutover).

Adds:
  - scripts/earnings/builders/eight_k_packet.py
  - scripts/earnings/test_builders_eight_k_packet.py (8 mocked tests)

Verbatim copies of: build_8k_packet, _fetch_8k_core, QUERY_4J, QUERY_4K,
QUERY_4G_META, QUERY_4K_OTHER_PREVIEW, QUERY_4F.
```

**Rollback (1.1):** `git revert HEAD` — removes both new files; warmup_cache.py untouched.

#### Stage 1.2 CUTOVER — subtractive, warmup_cache becomes a re-exporter

**Goal:** delete the moved defs from `warmup_cache.py` and replace with the re-export block. After this commit, `eight_k_packet.py` is the sole canonical home.

**What changes:**

- MODIFIED: `scripts/earnings/builders/warmup_cache.py` (delete blocks, add import block)
- MODIFIED: `scripts/earnings/test_builders_imports.py` (add stand-alone `test_eight_k_packet_canonical_facade_identity`; do NOT add to MODULE_PAIRS — see §2.3; do NOT modify `test_builders_surface.py` either)

**Edits:**

1. In `warmup_cache.py`, delete:

   - Lines 258–262 (`QUERY_4J`)
   - Lines 264–269 (`QUERY_4K`)
   - Lines 271–293 (`QUERY_4G_META`)
   - Lines 295–305 (`QUERY_4K_OTHER_PREVIEW`)
   - Lines 307–313 (`QUERY_4F`)
   - Lines 420–431 (the SHARED OWNERSHIP WARNING comment block — moved into eight_k_packet.py with text refresh)
   - Lines 433–440 (`_fetch_8k_core` def)
   - Lines 466–562 (`build_8k_packet` def)

   Use 8 separate `Edit` operations, each removing one fenced block. Provide ample surrounding context to make `old_string` unique.

2. Right AFTER the existing `from neograph.Neo4jConnection import get_manager` line (currently warmup_cache.py:39), insert the eight_k_packet re-export block:

   ```python
   # ── Domain-module re-exports — back-compat for adapters, tests, .claude shim ──
   # Stage 1.2: 8-K packet domain (eight_k_packet.py)
   from .eight_k_packet import (
       build_8k_packet,
       _fetch_8k_core,
       QUERY_4J,
       QUERY_4K,
       QUERY_4G_META,
       QUERY_4K_OTHER_PREVIEW,
       QUERY_4F,
   )
   # Stage 2.2: guidance history re-exports will be added here
   # Stage 3.2: inter-quarter context re-exports will be added here
   ```

3. Verify `run_8k()` (currently warmup_cache.py:443–463) STILL references `_fetch_8k_core(manager, accession)` unqualified. The re-exported binding makes this resolve to the canonical eight_k_packet object — no edit needed inside `run_8k`.

4. **DO NOT add `eight_k_packet` to `EXPECTED_SURFACE` in `test_builders_surface.py`.** That dict is keyed by BARE module names — `test_module_exposes_expected_surface` calls `importlib.import_module("eight_k_packet")` (line 55), which would fail because the canonical module lives at `scripts.earnings.builders.eight_k_packet`, NOT at a bare-importable path. Additionally, `test_module_pairs_completeness` (test_builders_imports.py:321) asserts every EXPECTED_SURFACE entry has a `MODULE_PAIRS` row — adding `"eight_k_packet"` to one without the other red-flags both tests.

   Instead, the per-domain surface is covered by the parametrize lists in `test_builders_warmup_split.py` (`_EIGHTK_SYMBOLS` already lists `build_8k_packet`, `_fetch_8k_core`, plus all 5 query constants — strictly more than the 2-symbol surface that would have been added). No per-domain `EXPECTED_SURFACE` entry is needed.

   The existing `EXPECTED_SURFACE["warmup_cache"]` row STAYS UNCHANGED — every symbol still reachable via `warmup_cache.X` (re-export). The parametrize-based identity tests in `test_builders_warmup_split.py` are the primary canonical-side surface coverage.

5. **DECISION (locked):** Add the stand-alone identity test below to `test_builders_imports.py`. Do NOT thread a synthetic `"eight_k_packet_facade"` row through `MODULE_PAIRS` — the parametrize machinery there assumes "old bare path" is a real import target, which a domain-only module doesn't have. The stand-alone test below gives identical signal with simpler maintenance.

   ```python
   def test_eight_k_packet_canonical_facade_identity():
       """Stage 1.2 facade contract: warmup_cache re-exports preserve identity
       with eight_k_packet canonical home."""
       import scripts.earnings.builders.warmup_cache as wc
       import scripts.earnings.builders.eight_k_packet as ek
       for sym in ("build_8k_packet", "_fetch_8k_core",
                   "QUERY_4J", "QUERY_4K", "QUERY_4G_META",
                   "QUERY_4K_OTHER_PREVIEW", "QUERY_4F"):
           f = getattr(wc, sym, None)
           c = getattr(ek, sym, None)
           assert c is not None, f"eight_k_packet missing {sym}"
           assert f is not None, f"warmup_cache facade missing {sym}"
           assert f is c, f"facade {sym} != canonical {sym}"
   ```

6. Add a `# _fetch_8k_core re-exported from .eight_k_packet — same object, used by build_8k_packet too` comment immediately above `def run_8k(...)` in `warmup_cache.py` (REQUIRED — makes the shared-ownership contract visible to a future maintainer who edits `run_8k`).

7. Extend `test_builders_imports.py::test_concurrent_imports_preserve_identity` — locate the `mods_to_import` list (around line 358) and APPEND `"scripts.earnings.builders.eight_k_packet"` to it. (Stages 2.2 and 3.2 will append `guidance_history` and `inter_quarter_context` respectively. This guards against parallel-import races for the new module.)

8. Add `test_run_8k_uses_canonical_fetch_8k_core` to `test_builders_imports.py` (NOT to `test_builders_eight_k_packet.py` — the test exercises the FACADE behavior, which is an integration-style identity check across two modules):

   ```python
   def test_run_8k_uses_canonical_fetch_8k_core():
       """Stage 1.2 LOAD-BEARING contract: warmup_cache.run_8k() and
       eight_k_packet.build_8k_packet() share the SAME _fetch_8k_core object.

       This is sufficient as identity-only — DO NOT add a `with patch(...)` block
       that patches `scripts.earnings.builders.eight_k_packet._fetch_8k_core` and
       calls `wc.run_8k(...)`. That patch would NOT take effect because:
       (a) `from .eight_k_packet import _fetch_8k_core` snapshots the binding into
           `warmup_cache.__dict__['_fetch_8k_core']` at import time;
       (b) `wc.run_8k` body does an unqualified `_fetch_8k_core(...)` lookup against
           `wc.run_8k.__globals__` (which IS `warmup_cache.__dict__`);
       (c) `mock.patch("scripts.earnings.builders.eight_k_packet._fetch_8k_core")`
           rebinds `eight_k_packet.__dict__['_fetch_8k_core']` ONLY — it does NOT
           reach into `warmup_cache.__dict__`.
       The identity assertion below is sufficient and correct."""
       import scripts.earnings.builders.warmup_cache as wc
       import scripts.earnings.builders.eight_k_packet as ek
       assert wc._fetch_8k_core is ek._fetch_8k_core, (
           f"shared-ownership BROKEN: wc._fetch_8k_core (id={id(wc._fetch_8k_core)}) "
           f"is not ek._fetch_8k_core (id={id(ek._fetch_8k_core)}) — "
           f"warmup_cache.py must use `from .eight_k_packet import _fetch_8k_core`, "
           f"NOT define its own def"
       )
       # Bonus: assert run_8k's __globals__ resolves _fetch_8k_core to the canonical
       # object — proves the function looks up the name in the right namespace
       assert wc.run_8k.__globals__["_fetch_8k_core"] is ek._fetch_8k_core, (
           "run_8k.__globals__['_fetch_8k_core'] is not the canonical eight_k_packet object"
       )
   ```

**Gate (Stage 1.2):**

```bash
set -euo pipefail
cd /home/faisal/em-warmup-cache-split
PY=/home/faisal/EventMarketDB/venv/bin/python

# 1. warmup_cache.py compiles AND its imports actually resolve.
#    py_compile alone only checks syntax — relative imports (`from .eight_k_packet import ...`)
#    are NOT verified at compile time. A typo in a re-exported symbol name would pass
#    py_compile but fail at runtime. Add a real import check.
$PY -m py_compile scripts/earnings/builders/warmup_cache.py
# expect: silent
PYTHONPATH=. $PY -c "
from scripts.earnings.builders import warmup_cache as wc
from scripts.earnings.builders import eight_k_packet as ek
for sym in ('build_8k_packet', '_fetch_8k_core', 'QUERY_4J', 'QUERY_4K',
            'QUERY_4G_META', 'QUERY_4K_OTHER_PREVIEW', 'QUERY_4F'):
    f, c = getattr(wc, sym, None), getattr(ek, sym, None)
    assert c is not None, f'eight_k_packet.{sym} missing'
    assert f is not None, f'warmup_cache.{sym} missing — re-export incomplete'
    assert f is c, f'IDENTITY BROKEN for {sym}'
print('warmup_cache imports resolve + identity holds for all 7 eight_k_packet symbols')
"

# 2. ONE def per moved symbol (no duplicates). SCOPE the grep to ONLY warmup_cache.py
#    AND eight_k_packet.py — adapters.py:107 ALSO defines `def build_8k_packet(ticker, ...)`
#    as the orchestrator-facing wrapper (verified). A bare `grep -rn scripts/earnings/builders/`
#    would count 2 (canonical + adapter wrapper) and spuriously fail. The two files below
#    are the ONLY legitimate locations for the canonical relocated def post-cutover.
for name in build_8k_packet _fetch_8k_core; do
    count=$(grep -c "^def $name" scripts/earnings/builders/warmup_cache.py scripts/earnings/builders/eight_k_packet.py 2>/dev/null | awk -F: '{s+=$NF} END {print s}')
    echo "$name: $count def(s) (across warmup_cache.py + eight_k_packet.py)"
    test "$count" -eq 1 || { echo "FAIL: expected exactly 1 def for $name in the two scoped files"; exit 1; }
done
for q in QUERY_4J QUERY_4K QUERY_4G_META QUERY_4K_OTHER_PREVIEW QUERY_4F; do
    count=$(grep -c "^${q} = " scripts/earnings/builders/warmup_cache.py scripts/earnings/builders/eight_k_packet.py 2>/dev/null | awk -F: '{s+=$NF} END {print s}')
    echo "$q: $count"
    test "$count" -eq 1 || { echo "FAIL: expected exactly 1 assignment for $q"; exit 1; }
done

# 3. Identity tests — facade matches canonical
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_warmup_split.py::test_facade_reexports_match_eight_k_packet_canonical -v
# expect: 7 passed (one per symbol in _EIGHTK_SYMBOLS)
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_imports.py::test_eight_k_packet_canonical_facade_identity -v
# expect: 1 passed

# 4. Surface test still passes (UNCHANGED — we don't touch test_builders_surface.py per §2.3)
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_surface.py -v
# expect: exit code 0 with the same baseline pass count (no new entries added; warmup_cache row preserved)

# 5. Existing 4-path identity tests — warmup_cache row UNCHANGED, still passes
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_imports.py -v -m "not live"
# expect: every existing identity test still green

# 6. run_8k still works (mocked) — patch warmup_cache.get_manager because run_8k
#    is DEFINED in warmup_cache.py and looks up `get_manager` in wc's globals
#    (where neograph's get_manager is bound at import time). Patching
#    eight_k_packet.get_manager would NOT affect wc's lookup — different namespaces.
PYTHONPATH=scripts/earnings $PY -c "
from unittest.mock import MagicMock, patch
mgr = MagicMock()
mgr.execute_cypher_query_all.return_value = []
mgr.close = MagicMock()
with patch('scripts.earnings.builders.warmup_cache.get_manager', return_value=mgr):
    import scripts.earnings.builders.warmup_cache as wc
    wc.run_8k('ACC')
    print('run_8k OK')
"
# expect: run_8k OK

# 7. Static no-back-import (skipped before because eight_k_packet didn't exist)
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_warmup_split.py::test_no_warmup_cache_back_imports -v
# expect: passed (no skip)

# 8. CLI --test still works (defs that --test exercises still live in warmup_cache for now)
PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache --test
PYTHONPATH=scripts/earnings $PY .claude/skills/earnings-orchestrator/scripts/warmup_cache.py --test
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh --test
# expect: all pass — count unchanged

# 9. Full builders test matrix — exit code 0 is the gate. Do NOT lock to a specific
#    count (the count drifts as tests are added/removed and as parametrized cases
#    activate/skip per stage). The §6.8 Required Gates block + the per-stage identity
#    tests collectively prove correctness; total count is observability only.
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_*.py -q -m "not live"
# expect: exit code 0 (capture the count for your records but do not gate on it)

# 10. Renderer suite UNCHANGED
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_renderer_*.py -q
# expect: same count as pre-flight
```

**Commit message (1.2):**

```
refactor(builders): cutover 8-K packet symbols to eight_k_packet (commit 3/10)

warmup_cache.py is now a facade that re-exports build_8k_packet, _fetch_8k_core,
and 5 query constants from .eight_k_packet. Identity preserved by direct
re-export — `from warmup_cache import build_8k_packet is from eight_k_packet
import build_8k_packet` (verified by new identity tests).

run_8k continues to call _fetch_8k_core via the warmup_cache facade — same
canonical object as build_8k_packet uses.

Adds:
  - test_builders_imports.py: test_eight_k_packet_canonical_facade_identity
  - (no EXPECTED_SURFACE edit — per §2.3 plan decision)
Removes:
  - warmup_cache.py: 5 query defs, _fetch_8k_core, build_8k_packet,
    SHARED OWNERSHIP comment block (moved into eight_k_packet.py).
```

**Rollback (1.2):** `git revert HEAD` — restores the moved blocks into warmup_cache.py and removes the re-export. Stage 1.1's eight_k_packet.py remains; the canonical home temporarily becomes "both files have the def" again.

---

### Stage 2 — Extract `guidance_history.py` (2 commits)

#### Stage 2.1 COPY

**Goal:** create the canonical guidance_history module with verbatim copies. `warmup_cache.py` UNCHANGED.

**What changes:**

- NEW: `scripts/earnings/builders/guidance_history.py`
- NEW: `scripts/earnings/test_builders_guidance_history.py`

**Edits:** mirror Stage 1.1's structure. Copy verbatim:

- `_SOURCE_PRIORITY` (warmup_cache.py:371)
- `_extract_given_day` (warmup_cache.py:374–377)
- `_normalize_qualitative` (warmup_cache.py:379–391)
- `resolve_unit_groups` (warmup_cache.py:393–417)
- `QUERY_GUIDANCE_HISTORY` (warmup_cache.py:321–343)
- `QUERY_GUIDANCE_HISTORY_PIT` (warmup_cache.py:345–368)
- `_format_value` (warmup_cache.py:573–639)
- `render_guidance_text` (warmup_cache.py:642–702)
- `build_guidance_history` (warmup_cache.py:705–929)
- `_run_v2_regression_tests` (warmup_cache.py:2003–2060)

Module preamble:

```python
#!/usr/bin/env python3
"""Guidance history builder — orchestration side.

Owns:
  - QUERY_GUIDANCE_HISTORY, QUERY_GUIDANCE_HISTORY_PIT
  - _SOURCE_PRIORITY (8k > transcript > 10q > 10k > news)
  - _extract_given_day, _normalize_qualitative, resolve_unit_groups
  - _format_value (numeric/qualitative formatter)
  - render_guidance_text(packet) -> str
  - build_guidance_history(ticker, pit=None, out_path=None) -> packet dict
  - _run_v2_regression_tests() -> bool   (CLI --test target, exercises
    _format_value + resolve_unit_groups)

Re-exported from scripts.earnings.builders.warmup_cache for back-compat.
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

from ._paths import ensure_legacy_paths
ensure_legacy_paths()

from neograph.Neo4jConnection import get_manager


# ── Source priority: 8k > transcript > 10q > 10k > news ───────────────
_SOURCE_PRIORITY = {'8k': 0, 'transcript': 1, '10q': 2, '10k': 3, 'news': 4}


# ── Cypher (verbatim from warmup_cache.py:321-368) ────────────────────
QUERY_GUIDANCE_HISTORY = """ ... """
QUERY_GUIDANCE_HISTORY_PIT = """ ... """


# ── Helpers ───────────────────────────────────────────────────────────
def _extract_given_day(ts):
    """..."""  # verbatim


def _normalize_qualitative(q):
    """..."""  # verbatim


def resolve_unit_groups(rows):
    """..."""  # verbatim


def _format_value(low, mid, high, unit, qualitative, derivation):
    """..."""  # verbatim


def render_guidance_text(packet):
    """..."""  # verbatim


def build_guidance_history(ticker, pit=None, out_path=None):
    """..."""  # verbatim


def _run_v2_regression_tests():
    """..."""  # verbatim — note this function references _format_value and
                # resolve_unit_groups defined ABOVE in this module, so no
                # cross-module imports are needed.
```

`test_builders_guidance_history.py` mirrors Stage 1.1's pattern with mocked tests for:

- empty guidance returns valid empty packet
- PIT vs live query selection (assert correct query string passed to manager)
- `resolve_unit_groups` unknown remap (one real unit) and no-remap (mixed units)
- numeric duplicate collapse by (fy, fq, day, low, mid, high)
- qualitative duplicate collapse after `_normalize_qualitative`
- source-priority ordering in the merged `sources` list
- richest conditions selection (longest non-null wins)
- richest qualitative selection (longest non-null wins)
- member_qnames union + sort
- series sort: alphabetical by metric, total first within metric_id
- `_format_value` edge cases — negative range uses "to" not "-"; basis_points uses "to" too; m_usd unit-suffix stripping
- rendered text header — verifies cutoff annotation when pit set
- rendered text **conditions truncation** — when a guidance row's `conditions` field exceeds the 100-char render budget, the rendered string ends with `...` and must NOT exceed the cap (renderer parity with the prior outline's bullet)
- richest-conditions **cross-source** coverage — explicitly construct a collapse group with non-null conditions of differing length from 8-K + transcript + 10-Q rows and assert the longest wins (extends the generic "richest conditions" bullet with explicit cross-source data)
- member_qname union **cross-source** sort — same construction as above for `member_qnames`; assert the union spans all three source rows AND the resulting list is sorted alphabetically
- `_run_v2_regression_tests()` returns True (the existing test suite still passes inside the new module)

**Gate (2.1):** mirror Stage 1.1 gate, scaled to guidance_history. CRITICAL extra check:

```bash
set -euo pipefail
# guidance_history._run_v2_regression_tests() works in isolation
PYTHONPATH=scripts/earnings $PY -c "
from scripts.earnings.builders.guidance_history import _run_v2_regression_tests
assert _run_v2_regression_tests() is True, 'inline regression suite failed'
print('OK')
"
# expect: OK
```

**Commit message (2.1):**

```
refactor(builders): copy guidance history symbols into guidance_history.py (commit 4/10)

Verbatim additive copy. Cutover in commit 5/10.

Adds:
  - scripts/earnings/builders/guidance_history.py
  - scripts/earnings/test_builders_guidance_history.py (~12 mocked tests)

Symbols copied: _SOURCE_PRIORITY, _extract_given_day, _normalize_qualitative,
resolve_unit_groups, _format_value, render_guidance_text, build_guidance_history,
_run_v2_regression_tests, QUERY_GUIDANCE_HISTORY, QUERY_GUIDANCE_HISTORY_PIT.
```

#### Stage 2.2 CUTOVER

**Goal:** delete moved defs from `warmup_cache.py`, extend the re-export block, extend test surface + identity guards.

**What changes:**

- MODIFIED: `scripts/earnings/builders/warmup_cache.py`
- MODIFIED: `scripts/earnings/test_builders_imports.py` (do NOT modify `test_builders_surface.py` — see §2.3 plan decision)

**Edits:**

1. Delete from `warmup_cache.py`:
   - Lines 321–343 (`QUERY_GUIDANCE_HISTORY`)
   - Lines 345–368 (`QUERY_GUIDANCE_HISTORY_PIT`)
   - Line 371 (`_SOURCE_PRIORITY`)
   - Lines 374–377 (`_extract_given_day`)
   - Lines 379–391 (`_normalize_qualitative`)
   - Lines 393–417 (`resolve_unit_groups`)
   - Lines 565–570 (the `─── build_guidance_history() — EARNINGS ORCHESTRATION only ───` comment block — moved into guidance_history.py docstring)
   - Lines 573–639 (`_format_value`)
   - Lines 642–702 (`render_guidance_text`)
   - Lines 705–929 (`build_guidance_history`)
   - Lines 2003–2060 (`_run_v2_regression_tests`)

2. Extend the re-export block in `warmup_cache.py` (under the existing `# Stage 2.2:` placeholder comment):

   ```python
   # Stage 2.2: guidance history domain (guidance_history.py)
   from .guidance_history import (
       build_guidance_history,
       render_guidance_text,
       resolve_unit_groups,
       _format_value,
       _extract_given_day,
       _normalize_qualitative,
       _SOURCE_PRIORITY,
       QUERY_GUIDANCE_HISTORY,
       QUERY_GUIDANCE_HISTORY_PIT,
       _run_v2_regression_tests,
   )
   ```

3. Verify the `if __name__ == "__main__"` block at the bottom of `warmup_cache.py` (lines 2063–2065) still works — the `_run_v2_regression_tests` it calls is now the re-exported binding from guidance_history. Same object identity, same behavior.

4. **DO NOT add `guidance_history` to `EXPECTED_SURFACE`.** Same rationale as Stage 1.2 step 4 — `EXPECTED_SURFACE` is bare-import-keyed and `test_module_pairs_completeness` requires MODULE_PAIRS coverage. The per-domain surface is fully covered by `_GUIDANCE_SYMBOLS` in `test_builders_warmup_split.py` (which already lists all 10 relocated symbols including the 2 query constants).

   Add ONLY the stand-alone identity test `test_guidance_history_canonical_facade_identity` to `test_builders_imports.py` (mirroring Stage 1.2 step 5 pattern).

   The existing `EXPECTED_SURFACE["warmup_cache"]` row STAYS UNCHANGED.

5. **Append `"scripts.earnings.builders.guidance_history"` to the `mods_to_import` list in `test_builders_imports.py::test_concurrent_imports_preserve_identity`** (parallel-import safety guard for the new domain module — mirror the Stage 1.2 step 7 pattern).

6. **Re-export ordering:** add the new `from .guidance_history import (...)` block AFTER the existing `from .eight_k_packet import (...)` block (added in Stage 1.2). Keep the order `eight_k_packet → guidance_history → inter_quarter_context` because (a) it matches the order symbols were originally defined in warmup_cache.py (8-K queries before guidance before IQ), (b) it makes the diff at every cutover trivially reviewable.

**Gate (2.2):** mirror Stage 1.2 gate, plus:

```bash
set -euo pipefail
# CRITICAL: --test still works through every CLI path (uses re-exported _run_v2_regression_tests)
PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache --test
PYTHONPATH=scripts/earnings $PY .claude/skills/earnings-orchestrator/scripts/warmup_cache.py --test
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh --test
# expect: all pass with same count

# warmup_cache.py size is shrinking
wc -l scripts/earnings/builders/warmup_cache.py
# expect: ~1300 lines (down from 2066)
```

**Commit message (2.2):**

```
refactor(builders): cutover guidance history symbols to guidance_history (commit 5/10)

warmup_cache.py re-exports build_guidance_history, render_guidance_text, +
8 helpers/queries from .guidance_history. _run_v2_regression_tests now lives
in guidance_history.py — invoked unchanged via warmup_cache __main__ block
through the re-exported binding (same Python object).

warmup_cache.py: ~2066 → ~1300 lines.
```

---

### Stage 3 — Extract `inter_quarter_context.py` (2 commits)

#### Stage 3.1 COPY

**Goal:** create the canonical inter_quarter_context module with verbatim copies of ~17 helpers + 6 queries + 2 public functions. `warmup_cache.py` UNCHANGED.

**What changes:**

- NEW: `scripts/earnings/builders/inter_quarter_context.py`
- NEW: `scripts/earnings/test_builders_inter_quarter_context.py`

**Edits:** mirror Stage 1.1 / 2.1. Copy verbatim:

- 6 `QUERY_IQ_*` constants (warmup_cache.py:940–1068)
- `_iq_parse_json_field`, `_norm_ret`, `_fmt_vol`, `_fmt_txn`, `_safe_adj`, `_event_ref`, `_day_from_ts` (warmup_cache.py:1073–1126)
- `_parse_dt_for_pit` (warmup_cache.py:1128–1143)
- `_is_price_pit_safe` (warmup_cache.py:1146–1158)
- `_build_forward_returns` (warmup_cache.py:1160–1210)
- `_cutoff_boundary_price_role` (warmup_cache.py:1213–1221)
- `_best_safe_horizon` (warmup_cache.py:1223–1235)
- `_report_summary` (warmup_cache.py:1238–1247)
- `_render_window_label_news`, `_render_window_label_filing`, `_render_horizon_line_filing`, `_render_news_react_line` (warmup_cache.py:1253–1320)
- `render_inter_quarter_text` (warmup_cache.py:1323–1493)
- `build_inter_quarter_context` (warmup_cache.py:1496–1879)

Module preamble:

```python
#!/usr/bin/env python3
"""Inter-quarter context builder — orchestration side.

Owns:
  - QUERY_IQ_* (6 Cypher queries)
  - JSON / number / time helpers
  - _parse_dt_for_pit (DIFFERENT FUNCTION from peer_earnings_snapshot._parse_dt_for_pit;
    same name, intentionally distinct — see test_parse_dt_for_pit_disambiguation)
  - PIT safety gates (_is_price_pit_safe, _build_forward_returns, _cutoff_boundary_price_role)
  - Render helpers (_best_safe_horizon, _report_summary, _render_*)
  - render_inter_quarter_text(packet) -> str
  - build_inter_quarter_context(ticker, prev_8k_ts, context_cutoff_ts,
                                out_path=None, context_cutoff_reason=None) -> packet dict

Re-exported from scripts.earnings.builders.warmup_cache for back-compat.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone

from ._paths import ensure_legacy_paths
ensure_legacy_paths()

from neograph.Neo4jConnection import get_manager


# ... [verbatim symbol bodies, in original order] ...
```

CRITICAL: the lazy `from utils.market_session import MarketSessionClassifier` inside `build_inter_quarter_context` (currently warmup_cache.py:1509) is COPIED VERBATIM. The `_paths.ensure_legacy_paths()` already pinned `sys.modules['utils']` to the repo-root package — the same pin applies because both modules live at `scripts/earnings/builders/<X>.py` depth.

`test_builders_inter_quarter_context.py` mirrors prior pattern with mocked tests for:

- boundary day creation (prev_day, cutoff_day) when no price row covers them
- prev_boundary marked `reference_only`, cutoff_boundary depends on `_cutoff_boundary_price_role`
- cutoff-day price NULLED when bar timestamp post-cutoff or unparseable; KEPT when PIT-safe (early-close case)
- company-context fallback when price rows lack sector/industry
- news/filings/dividends/splits inserting synthetic non-trading day blocks
- forward returns nulled when horizon end > cutoff
- `_iq_parse_json_field` fallback for bad strings
- `_norm_ret` NaN, list, string normalization
- event sort order: timestamped before date-only, then type order (filing→news→dividend→split)
- significant move + gap day rules
- summary count correctness
- rendered text per branch — assert ALL six branches render correctly: **boundary** (prev_boundary + cutoff_boundary header), **gap** (significant move with no events), **ordinary** (trading day with events), **news**, **filing**, **dividend**, **split**. Each branch is load-bearing for renderer parity; do not collapse into a single test
- previous-boundary price ALWAYS marked `reference_only` even when PIT-safe — guards a subtle bug-class where someone "fixes" the prev boundary to use its own daily return; the prev boundary is reference-only by design regardless of safety
- early-close cutoff: cutoff-day price KEPT when bar timestamp ≤ cutoff AND bar comes from an early-close session (1pm close) — exercises the `_is_price_pit_safe` early-close branch and the price_role override that prevents the hour-heuristic from incorrectly setting reference_only
- `_norm_ret` **explicit input variants**: pass each of `(NaN, [list], "string", None, 0.0, large_negative=-12345.67)` and assert the expected output shape (None for NaN/None/string-non-numeric; the value for list[0]; 2-decimal-rounded float for the rest). Test each input case as its own assertion
- `_parse_dt_for_pit` works with `Z`, `-04:00`, `-0400`, space-separated formats

ALSO add a NEW test inside `test_builders_inter_quarter_context.py`:

```python
def test_parse_dt_for_pit_distinct_from_peer():
    """Mirror of the existing test_builders_imports.py shadow guard, scoped
    to the new canonical home. Stage 3.1 contract: inter_quarter_context's
    _parse_dt_for_pit is a DIFFERENT object from peer_earnings_snapshot's."""
    from scripts.earnings.builders.inter_quarter_context import _parse_dt_for_pit as iq_fn
    from scripts.earnings.builders.peer_earnings_snapshot import _parse_dt_for_pit as peer_fn
    assert iq_fn is not peer_fn, "shadow violation: same object across modules"
```

**Gate (3.1):** mirror prior stages + extra:

```bash
set -euo pipefail
# Verify _parse_dt_for_pit is a distinct function from peer's
PYTHONPATH=scripts/earnings $PY -c "
from scripts.earnings.builders.inter_quarter_context import _parse_dt_for_pit as a
from scripts.earnings.builders.peer_earnings_snapshot import _parse_dt_for_pit as b
assert a is not b, 'shadow broken'
print('shadow distinct OK')
"
# expect: shadow distinct OK
```

**Commit message (3.1):**

```
refactor(builders): copy inter-quarter context symbols (commit 6/10)

Verbatim additive copy. Cutover in commit 7/10.

Adds:
  - scripts/earnings/builders/inter_quarter_context.py
  - scripts/earnings/test_builders_inter_quarter_context.py (~15 mocked tests)

Symbols copied: 6 QUERY_IQ_* constants, _iq_parse_json_field, _norm_ret,
_fmt_vol, _fmt_txn, _safe_adj, _event_ref, _day_from_ts, _parse_dt_for_pit,
_is_price_pit_safe, _build_forward_returns, _cutoff_boundary_price_role,
_best_safe_horizon, _report_summary, _render_window_label_news,
_render_window_label_filing, _render_horizon_line_filing,
_render_news_react_line, render_inter_quarter_text, build_inter_quarter_context.

The new module's _parse_dt_for_pit remains a DIFFERENT object from
peer_earnings_snapshot's — same name, intentionally distinct.
```

#### Stage 3.2 CUTOVER

**Goal:** delete moved defs from `warmup_cache.py`, finalize the re-export block, extend tests + extend the existing shadow guard.

**What changes:**

- MODIFIED: `scripts/earnings/builders/warmup_cache.py`
- MODIFIED: `scripts/earnings/test_builders_imports.py` (do NOT modify `test_builders_surface.py` — see §2.3 plan decision)

**Edits:**

1. Delete from `warmup_cache.py`:
   - All 6 `QUERY_IQ_*` blocks
   - `_iq_*` helpers
   - `_norm_ret`, `_fmt_vol`, `_fmt_txn`, `_safe_adj`, `_event_ref`, `_day_from_ts`
   - `_parse_dt_for_pit`, `_is_price_pit_safe`, `_build_forward_returns`, `_cutoff_boundary_price_role`, `_best_safe_horizon`, `_report_summary`
   - All `_render_*` IQ helpers
   - `render_inter_quarter_text`
   - `build_inter_quarter_context`
   - The `─── build_inter_quarter_context() — EARNINGS ORCHESTRATION only ───` comment block at lines 932–937 (moved into the new module's docstring)

2. Extend the re-export block in `warmup_cache.py` (replacing the `# Stage 3.2:` placeholder):

   ```python
   # Stage 3.2: inter-quarter context domain (inter_quarter_context.py)
   from .inter_quarter_context import (
       build_inter_quarter_context,
       render_inter_quarter_text,
       _parse_dt_for_pit,
       _is_price_pit_safe,
       _build_forward_returns,
       _iq_parse_json_field,
       _norm_ret,
       _fmt_vol,
       _fmt_txn,
       _safe_adj,
       _event_ref,
       _day_from_ts,
       _cutoff_boundary_price_role,
       _best_safe_horizon,
       _report_summary,
       _render_window_label_news,
       _render_window_label_filing,
       _render_horizon_line_filing,
       _render_news_react_line,
       QUERY_IQ_PRICES,
       QUERY_IQ_NEWS,
       QUERY_IQ_FILINGS,
       QUERY_IQ_DIVIDENDS,
       QUERY_IQ_SPLITS,
       QUERY_IQ_COMPANY_CONTEXT,
   )
   ```

3. **DO NOT add `inter_quarter_context` to `EXPECTED_SURFACE`.** Same rationale as Stages 1.2 / 2.2 — bare-import-keyed dict + completeness test would both red-flag. The per-domain surface is fully covered by `_IQ_SYMBOLS` in `test_builders_warmup_split.py` (25 symbols including all 6 IQ query constants and `_parse_dt_for_pit`).

4. Add stand-alone identity test `test_inter_quarter_context_canonical_facade_identity` in `test_builders_imports.py` (mirroring Stage 1.2/2.2 pattern), covering all 25 listed symbols. The existing `EXPECTED_SURFACE["warmup_cache"]` row STAYS UNCHANGED.

4b. **Append `"scripts.earnings.builders.inter_quarter_context"` to the `mods_to_import` list in `test_builders_imports.py::test_concurrent_imports_preserve_identity`** (parallel-import safety guard — mirror Stages 1.2 step 7 and 2.2 step 5).

4c. **Re-export ordering:** the new `from .inter_quarter_context import (...)` block goes AFTER the `.eight_k_packet` and `.guidance_history` blocks. Keep the order `eight_k_packet → guidance_history → inter_quarter_context` consistent across all three cutover commits.

5. **EXTEND** the existing `test_parse_dt_for_pit_disambiguation` test in `test_builders_imports.py:190–218`. Update the docstring + add new asserts so the canonical home is also covered:

   ```python
   def test_parse_dt_for_pit_disambiguation():
       """Stage 3.2-EXTENDED SHADOW GUARD.

       After the warmup_cache → 3-domain split, _parse_dt_for_pit's canonical
       home is scripts.earnings.builders.inter_quarter_context. The warmup_cache
       facade re-exports it — same object. peer_earnings_snapshot's same-named
       function remains a DIFFERENT object.

       Required identity invariants:
         - within-module: warmup_cache._parse_dt_for_pit IS scripts.earnings.builders.warmup_cache._parse_dt_for_pit
         - facade-vs-canonical: warmup_cache._parse_dt_for_pit IS inter_quarter_context._parse_dt_for_pit
         - within-module: peer_earnings_snapshot._parse_dt_for_pit IS scripts.earnings.builders.peer_earnings_snapshot._parse_dt_for_pit
         - cross-module distinctness: warmup IS NOT peer
       """
       import warmup_cache, peer_earnings_snapshot
       import scripts.earnings.builders.warmup_cache as wc_new
       import scripts.earnings.builders.peer_earnings_snapshot as pe_new
       import scripts.earnings.builders.inter_quarter_context as iq_new

       assert warmup_cache._parse_dt_for_pit is wc_new._parse_dt_for_pit, \
           "warmup_cache shim diverged from canonical for _parse_dt_for_pit"
       assert wc_new._parse_dt_for_pit is iq_new._parse_dt_for_pit, \
           "warmup_cache facade does NOT re-export inter_quarter_context._parse_dt_for_pit"
       assert peer_earnings_snapshot._parse_dt_for_pit is pe_new._parse_dt_for_pit, \
           "peer_earnings_snapshot shim diverged from canonical for _parse_dt_for_pit"
       assert warmup_cache._parse_dt_for_pit is not peer_earnings_snapshot._parse_dt_for_pit, (
           f"shadow violation: warmup_cache._parse_dt_for_pit "
           f"({id(warmup_cache._parse_dt_for_pit)}) IS the SAME object as "
           f"peer_earnings_snapshot._parse_dt_for_pit "
           f"({id(peer_earnings_snapshot._parse_dt_for_pit)})"
       )
   ```

**Gate (3.2):** mirror Stage 2.2 gate, plus:

```bash
set -euo pipefail
# Shadow guard now covers the canonical inter_quarter_context path
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_imports.py::test_parse_dt_for_pit_disambiguation -v
# expect: 1 passed

# Live test_builder_validation.py:602 ('from warmup_cache import _parse_dt_for_pit') still works.
# CRITICAL: this is a FRESH subprocess with bare `import warmup_cache` — needs the .claude
# skill-scripts dir on PYTHONPATH (that's where the bare-importable warmup_cache.py shim
# lives). PYTHONPATH=scripts/earnings ALONE would ModuleNotFoundError because there's no
# scripts/earnings/warmup_cache.py — only scripts/earnings/builders/warmup_cache.py.
PYTHONPATH=.claude/skills/earnings-orchestrator/scripts:scripts/earnings:. $PY -c "
from warmup_cache import _parse_dt_for_pit
from scripts.earnings.builders.inter_quarter_context import _parse_dt_for_pit as iq_fn
assert _parse_dt_for_pit is iq_fn, 'bare-import path broken'
print('bare-import OK')
"

wc -l scripts/earnings/builders/warmup_cache.py
# expect: ~520 lines (target after 3 stages)
```

**Commit message (3.2):**

```
refactor(builders): cutover inter-quarter context symbols (commit 7/10)

warmup_cache.py is now a pure facade for the 3 domain modules + the
extraction CLI (run_warmup, run_transcript, run_mda, run_8k, main).

Identity preserved by direct re-export. Existing shadow guard
test_parse_dt_for_pit_disambiguation extended to cover the new canonical
home (scripts.earnings.builders.inter_quarter_context._parse_dt_for_pit).

warmup_cache.py: ~1300 → ~520 lines.
```

---

### Stage 4 — Adapter canonicalization (1 commit, included per user-confirmed plan choice)

**Pre-edit verification (REQUIRED — do this before touching adapters.py):**

```bash
set -euo pipefail
cd /home/faisal/em-warmup-cache-split
PY=/home/faisal/EventMarketDB/venv/bin/python

# Stage 3.2 left adapters.py:42 patch target as scripts.earnings.builders.warmup_cache.build_8k_packet.
# Confirm it's actually green BEFORE editing — if it's not, Stage 3.2 has a hidden regression
# and Stage 4 must NOT proceed.
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_adapters.py -v
# expect: 6 passed (or whatever the post-Stage-3.2 baseline is — exit code 0 is the gate)
```

If this fails, STOP — Stage 3.2 isn't really done. Re-run §6.8 Required Gates against the Stage 3.2 commit; investigate; fix the underlying issue; only then return to Stage 4.

**Stage 4 is REQUIRED in this plan** (user-confirmed via AskUserQuestion). The Total commits = 10 ledger in §0/§7 includes it. The DAG-canonicalization keeps `adapters.py` symmetric with how `consensus.py`, `prior_financials.py`, etc. are imported there — without it, the adapter chain reaches the canonical domain via the `warmup_cache` facade hop, which works (identity preserved) but adds unnecessary indirection.

**Goal:** update the 3 lazy imports in `adapters.py` to point at canonical domain homes; update the corresponding test patch target.

**What changes:**

- MODIFIED: `scripts/earnings/builders/adapters.py`
- MODIFIED: `scripts/earnings/test_builders_adapters.py`

**Edits:**

1. In `adapters.py`:
   - Line 115: `from scripts.earnings.builders.warmup_cache import build_8k_packet as _legacy` → `from scripts.earnings.builders.eight_k_packet import build_8k_packet as _legacy`
   - Line 152: `from scripts.earnings.builders.warmup_cache import build_guidance_history as _legacy` → `from scripts.earnings.builders.guidance_history import build_guidance_history as _legacy`
   - Line 183: `from scripts.earnings.builders.warmup_cache import build_inter_quarter_context as _legacy` → `from scripts.earnings.builders.inter_quarter_context import build_inter_quarter_context as _legacy`

2. In `test_builders_adapters.py:42`:
   - `with patch("scripts.earnings.builders.warmup_cache.build_8k_packet", side_effect=SystemExit(1)):` → `with patch("scripts.earnings.builders.eight_k_packet.build_8k_packet", side_effect=SystemExit(1)):`

**Gate (Stage 4):**

```bash
set -euo pipefail
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_adapters.py -v
# expect: all pass
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_*.py -q -m "not live"
# expect: full matrix green
PYTHONPATH=scripts/earnings $PY scripts/earnings/earnings_orchestrator.py --test
# expect: 9 passed, 0 failed out of 9
```

**Commit message (4):**

```
refactor(builders): canonical adapter imports point at domain modules (commit 8/10)

adapters.py lazy imports now reference scripts.earnings.builders.eight_k_packet,
.guidance_history, .inter_quarter_context (canonical homes) instead of going
through the warmup_cache facade. Identity unchanged — both paths return the
same object — but the DAG is one hop shorter.

test_builders_adapters.py:42 patch target updated correspondingly.
```

---

### Stage 5 — Facade cleanup + permanent guards (1 commit)

**Goal:** prune now-unused imports from `warmup_cache.py`; refresh the module docstring; activate Stage-5 guards.

**What changes:**

- MODIFIED: `scripts/earnings/builders/warmup_cache.py`
**Edits:**

1. Audit `warmup_cache.py`'s `import` block at the top. After the split:
   - `import math` — was used by `_norm_ret` (now in `inter_quarter_context`, calls `math.isnan`). REMOVE.
   - `from collections import Counter, defaultdict` — were used by `build_guidance_history` and `build_inter_quarter_context` collapse logic (now in their domain modules). REMOVE.
   - `from datetime import datetime, timezone` — still used? CHECK with an AST scan over `Name` nodes (DON'T grep — the import line itself contains "datetime" and would false-positive a naive `rg` check):
     ```bash
     PYTHONPATH=. /home/faisal/EventMarketDB/venv/bin/python -c "
     import ast, pathlib
     t = ast.parse(pathlib.Path('scripts/earnings/builders/warmup_cache.py').read_text())
     # Strip the imports themselves before counting Name nodes
     body_only = [n for n in t.body if not isinstance(n, (ast.Import, ast.ImportFrom))]
     names = set()
     for n in body_only:
         for sub in ast.walk(n):
             if isinstance(sub, ast.Name):
                 names.add(sub.id)
     print('datetime referenced:', 'datetime' in names)
     print('timezone referenced:', 'timezone' in names)
     "
     ```
     If BOTH report False, REMOVE the import. If EITHER reports True, KEEP.
   - `import json`, `import os`, `import sys` — still used by `run_warmup` (json.dump), `main()` (sys.argv), etc. KEEP.
   - `from neograph.Neo4jConnection import get_manager` — still used by `run_warmup`, `run_transcript`, `run_mda`, `run_8k`. KEEP.
   - `from ._paths import ensure_legacy_paths` + `ensure_legacy_paths()` — still required for the lazy `from guidance_ids import normalize_for_member_match` in `_build_member_map`. KEEP.

2. Refresh the module docstring at the top of `warmup_cache.py`. Replace lines 1–27 with:

   ```python
   #!/usr/bin/env python3
   """Pre-fetch extraction caches AND facade for earnings-orchestration builders.

   This module owns:
     - Extraction CLI modes: run_warmup, run_transcript, run_mda, run_8k
     - Extraction Cypher: QUERY_2A, QUERY_2B, QUERY_MEMBER_MAP, QUERY_3B, QUERY_5B
     - _build_member_map (CIK-based member lookup)
     - main() — CLI dispatcher (8 modes)

   And it re-exports (for back-compat with adapters, the .claude shim, and
   existing tests) every symbol relocated to the three domain modules:
     - scripts.earnings.builders.eight_k_packet
     - scripts.earnings.builders.guidance_history
     - scripts.earnings.builders.inter_quarter_context

   Identity contract: every re-exported symbol resolves to the SAME Python
   object (Python `is`) as its canonical-domain counterpart. Verified by
   test_builders_warmup_split.py and test_builders_imports.py. DO NOT replace
   the re-export block with wrapper functions — that would silently break
   the identity invariant.

   Usage:
       warmup_cache.py TICKER                                   # 2A + 2B + MEMBER_MAP cache
       warmup_cache.py TICKER --transcript TRANSCRIPT_ID        # transcript content (3B)
       warmup_cache.py TICKER --mda ACCESSION                   # MD&A content (5B)
       warmup_cache.py TICKER --8k ACCESSION                    # 8-K sections + EX-99 (run_8k)
       warmup_cache.py TICKER --8k-packet ACCESSION             # 8k_packet.v1 (build_8k_packet)
       warmup_cache.py TICKER --guidance-history [--pit ISO]    # guidance_history.v1
       warmup_cache.py TICKER --inter-quarter --prev-8k ISO --context-cutoff ISO
       warmup_cache.py --test                                   # _run_v2_regression_tests

   Output paths under /tmp/earnings_*/transcript_*/mda_*/8k_content_*. See
   scripts/earnings/builders/{eight_k_packet,guidance_history,inter_quarter_context}.py
   for the orchestration packet schemas.
   """
   ```

3. **No marker file needed.** Stage-5 contract tests gate themselves intrinsically via three helpers in `test_builders_warmup_split.py` (Stage 0): `_all_reexport_blocks_present()` for the no-redefine assertion (activates at Stage 3.2, fails loudly on regression — does NOT self-disable on def re-introduction); `_all_cutovers_complete()` for the facade-size assertion; same helper for the 3 live structural-equality golden tests. After Stage 5's import cleanup + docstring refresh land, all three test families fire automatically. NO new committed file in this stage besides the modified `warmup_cache.py`.

**Gate (Stage 5):**

```bash
set -euo pipefail
cd /home/faisal/em-warmup-cache-split
PY=/home/faisal/EventMarketDB/venv/bin/python

# 1. Imports cleaned
$PY -c "
import ast, pathlib
tree = ast.parse(pathlib.Path('scripts/earnings/builders/warmup_cache.py').read_text())
imports = []
for n in ast.walk(tree):
    if isinstance(n, ast.Import):
        imports.extend(a.name for a in n.names)
    elif isinstance(n, ast.ImportFrom) and n.module:
        for a in n.names:
            imports.append(f'{n.module}.{a.name}')
# Hard-assert ALL THREE forbidden imports are gone. Previous version computed a
# `present` list but only asserted on `math` — Counter / defaultdict regressions
# would silently pass.
assert 'math' not in imports, 'import math not removed (was used by _norm_ret in inter_quarter_context)'
assert 'collections.Counter' not in imports, \
    'from collections import Counter not removed (was used by build_guidance_history)'
assert 'collections.defaultdict' not in imports, \
    'from collections import defaultdict not removed (was used by build_guidance_history + build_inter_quarter_context)'
print('imports clean (math, Counter, defaultdict all absent)')
"

# 2. Intrinsic Stage-5 gating active, contract tests pass loudly
PYTHONPATH=. $PY -c "
import sys; sys.path.insert(0, 'scripts/earnings')
from test_builders_warmup_split import _domain_modules_exist, _all_cutovers_complete
assert _domain_modules_exist(), '_domain_modules_exist() False — Stages 1.1/2.1/3.1 not done'
assert _all_cutovers_complete(), '_all_cutovers_complete() False — Stages 1.2/2.2/3.2 cutovers not done'
print('Stage 5 intrinsic checks: PASS')
"
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_warmup_split.py::test_facade_has_no_relocated_function_defs scripts/earnings/test_builders_warmup_split.py::test_facade_size_after_cleanup -v
# expect: 2 passed (no longer skipped — both intrinsic checks now True)

# 3. Goldens pass (live — requires Neo4j)
PYTHONPATH=. $PY -m pytest scripts/earnings/test_builders_warmup_split.py -v -m live
# expect: 3 golden tests PASSED. If Neo4j is unavailable, the goldens will FAIL with a
#         connection error (NOT silently skip). That is NOT a passing condition — STOP and
#         either (a) restore Neo4j connectivity then re-run, or (b) record an explicit
#         user-approved waiver in the PR description before merging. A "skipped due to
#         connection error" gate is NOT green.

# 4. Full builders matrix
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_*.py -q -m "not live"
# expect: full count green

# 5. Renderer suite UNCHANGED
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_renderer_*.py -q
# expect: same as pre-flight

# 6. Orchestrator --test 9/9
PYTHONPATH=scripts/earnings $PY scripts/earnings/earnings_orchestrator.py --test
# expect: 9 passed, 0 failed out of 9

# 7. CLI --test
PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache --test
PYTHONPATH=scripts/earnings $PY .claude/skills/earnings-orchestrator/scripts/warmup_cache.py --test
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh --test
# expect: all pass

# 8. Final size + symbol distribution check
wc -l scripts/earnings/builders/{warmup_cache,eight_k_packet,guidance_history,inter_quarter_context}.py
# expect: ~520, ~150, ~430, ~970
```

**Commit message (5):**

```
chore(builders): facade cleanup + Stage-5 contract activation (commit 9/10)

- Remove now-unused warmup_cache.py imports (math, Counter, defaultdict).
- Refresh module docstring to reflect facade role + extraction-CLI ownership.
- _all_reexport_blocks_present() (no-redefine assertion) and
  _all_cutovers_complete() (facade-size + live goldens) helpers in
  test_builders_warmup_split.py now return True — activates the static
  no-redefine assertion + facade-size assertion + 3 live structural-equality
  golden tests automatically. No marker file.

Final layout:
  warmup_cache.py            ~520 lines  (facade + extraction CLI + main)
  eight_k_packet.py          ~150 lines
  guidance_history.py        ~430 lines
  inter_quarter_context.py   ~970 lines
```

---

### Stage 6 — Documentation (1 commit, MANDATORY)

**Goal:** update `scripts/earnings/builders/README.md` to reflect the new layout. Zero-risk, useful for future maintainers.

**What changes:**

- MODIFIED: `scripts/earnings/builders/README.md`

**Edits:**

1. Replace the "## Layout" table with:

   ```markdown
   ## Layout

   | File | Responsibility |
   |---|---|
   | `_paths.py` | Centralized repo-root + `sys.path` discipline (load-bearing helper) |
   | `adapters.py` | Uniform adapter wrappers around the underlying builders |
   | `consensus.py` | Consensus history (Alpha Vantage + Yahoo fallback) |
   | `prior_financials.py` | Prior financial trends + revenue splits |
   | `macro_snapshot.py` | Macro snapshot (indicators + Benzinga via pit_fetch) |
   | `peer_earnings_snapshot.py` | Peer earnings snapshot (top-N same-industry peers) |
   | `warmup_cache.py` | **Facade + extraction CLI**: `run_warmup`, `run_transcript`, `run_mda`, `run_8k`, `main`; re-exports all 3 orchestration domain modules below |
   | `eight_k_packet.py` | `build_8k_packet` + `_fetch_8k_core` + 8-K Cypher (8k_packet.v1) |
   | `guidance_history.py` | `build_guidance_history` + `render_guidance_text` + guidance helpers + `_run_v2_regression_tests` (guidance_history.v1) |
   | `inter_quarter_context.py` | `build_inter_quarter_context` + `render_inter_quarter_text` + IQ helpers + `_parse_dt_for_pit` (inter_quarter_context.v1) |
   ```

2. Add a new section "## warmup_cache facade contract":

   ```markdown
   ## warmup_cache facade contract

   `warmup_cache.py` is a hybrid module: it owns the extraction CLI
   (`run_warmup`/`run_transcript`/`run_mda`/`run_8k`/`main`) AND re-exports
   every symbol relocated to `eight_k_packet.py`, `guidance_history.py`, and
   `inter_quarter_context.py`. Re-export uses direct module-level imports:

   ```python
   from .eight_k_packet import build_8k_packet, _fetch_8k_core, ...
   from .guidance_history import build_guidance_history, ...
   from .inter_quarter_context import build_inter_quarter_context, ...
   ```

   **Identity contract:** every re-exported symbol MUST resolve via Python `is`
   to the SAME object as its canonical-domain counterpart. NEVER replace the
   re-export with a wrapper function — that creates a new function object and
   silently breaks every identity test (`test_builders_imports.py`,
   `test_builders_warmup_split.py`).

   **Why a facade?** The 3 domain modules are pure orchestration; the
   extraction CLI lives ONLY in `warmup_cache.py`. Splitting `warmup_cache.py`
   entirely would force adapters, the `.claude/skills` shim, and the existing
   test suite (which uses `from warmup_cache import build_X`) to update
   imports. The facade keeps every external consumer working unchanged.
   ```

3. Refresh the line-count table at the bottom of the README:

   ```markdown
   ## Test surface

   | Test file | Count | What it asserts |
   |---|---|---|
   | (existing rows unchanged) | | |
   | `test_builders_warmup_split.py` | ~45 | Pre-/post-split goldens (FIVE), facade-vs-canonical identity per symbol per domain, no-back-imports static check |
   | `test_builders_eight_k_packet.py` | ~8 | Mocked: ValueError on missing meta, items JSON parse, null stripping, exhibit preview diff, filing text fallback, atomic write, manager.close on success+exception |
   | `test_builders_guidance_history.py` | ~12 | Mocked: empty packet, PIT vs live query, unit remap, dup collapse (numeric + qualitative), source priority, richest selection, member union/sort, series sort, _format_value edges, render header/cutoff |
   | `test_builders_inter_quarter_context.py` | ~15 | Mocked: boundary roles, PIT-safe price gating, fallback context, synthetic days, forward-return nulling, JSON parse fallback, NaN/list normalization, event sort, sig+gap rules, summary counts, render branches, _parse_dt_for_pit format coverage |
   ```

**Gate (Stage 6):**

```bash
set -euo pipefail
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_*.py -q -m "not live"
# expect: full matrix green
```

**Commit message (6):**

```
docs(builders): document warmup_cache facade + 3-domain layout (commit 10/10)

Updates README to reflect post-split layout and the facade contract.
Adds a new section explaining why warmup_cache is a hybrid (facade +
extraction CLI) and why direct re-export (NOT wrapper functions) is the
required pattern.
```

---

## 9. Merge + Cleanup

### 9.1 Pre-merge production quiescence

```bash
set -euo pipefail
echo "=== Redis queue depth (extract:pipeline) ==="
kubectl -n infrastructure exec deploy/redis -- redis-cli LLEN extract:pipeline
# expect: 0

echo "=== extraction-worker pods ==="
kubectl -n processing get pods -l app=extraction-worker --no-headers
# expect: empty (KEDA at 0/0)

echo "=== KEDA scaler state ==="
kubectl -n processing get scaledobject extraction-worker-scaler --no-headers
```

If queue is non-empty OR a pod is starting, EITHER wait for natural drain or pause KEDA temporarily:

```bash
kubectl -n processing annotate scaledobject extraction-worker-scaler \
    autoscaling.keda.sh/paused-replicas="0" --overwrite
```

After merge + post-merge gate, unpause:

```bash
kubectl -n processing annotate scaledobject extraction-worker-scaler \
    autoscaling.keda.sh/paused-replicas-
```

### 9.2 Tag main BEFORE merge for tag-based rollback

```bash
set -euo pipefail
cd /home/faisal/EventMarketDB
git checkout main
git pull --ff-only origin main
git tag pre-warmup-split-main-before-merge HEAD
```

### 9.3 ff-merge

```bash
set -euo pipefail
git merge --ff-only warmup-cache-domain-split
echo "main HEAD: $(git rev-parse HEAD | head -c 8)"
```

If `--ff-only` aborts, ABORT — do NOT do a merge commit. Investigate divergence (someone committed to main during your worktree work). Rebase the worktree branch onto current main, re-run gates, and try again.

### 9.4 Post-merge gate (re-run on main)

```bash
set -euo pipefail
cd /home/faisal/EventMarketDB
PY=/home/faisal/EventMarketDB/venv/bin/python
set -a; source .env; set +a
PYTHONPATH=. $PY -m pytest scripts/earnings/test_builders_paths.py -q
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_*.py -q -m "not live"
PYTHONPATH=scripts/earnings $PY scripts/earnings/earnings_orchestrator.py --test
PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache --test
PYTHONPATH=scripts/earnings $PY .claude/skills/earnings-orchestrator/scripts/warmup_cache.py --test
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh --test
# REQUIRED live validation — Neo4j MUST be reachable; a connection-error skip is NOT a
# passing condition. Either restore Neo4j connectivity then re-run, or record an explicit
# user-approved waiver in the merge commit / PR description before declaring the merge done:
PYTHONPATH=. $PY -m pytest scripts/earnings/test_builders_warmup_split.py -v -m live
PYTHONPATH=scripts/earnings $PY scripts/earnings/test_builder_validation.py --ticker FIVE
PYTHONPATH=scripts/earnings $PY scripts/earnings/test_adapter_validation.py --ticker FIVE
```

### 9.5 Cleanup worktree + branch

```bash
set -euo pipefail
git worktree remove /home/faisal/em-warmup-cache-split
git branch -d warmup-cache-domain-split
```

### 9.6 Optional push

```bash
set -euo pipefail
git push origin main
git push origin pre-warmup-split-main-before-merge   # preserve rollback tag remotely
```

### 9.7 Rollback (if post-merge failure)

Before push, undo with reset:

```bash
git reset --hard pre-warmup-split-main-before-merge
```

After push, revert range with one inverse commit per original:

```bash
set -euo pipefail
git revert --no-edit pre-warmup-split-main-before-merge..HEAD
git push origin main
```

KEDA's next scale-up picks up the reverted code.

---

## 10. Edge Cases & Gotchas

### 10.1 Don't drop `defaultdict`/`Counter`/`math` until Stage 5

After Stage 1.2 cutover, `_fetch_8k_core` and `build_8k_packet` are gone from `warmup_cache.py` — but `build_guidance_history` and `build_inter_quarter_context` are still there in Stages 1.2 → 2.1, and they use `Counter` + `defaultdict`. Removing those imports too early breaks the still-resident defs. Wait until Stage 5.

### 10.2 The lazy `from guidance_ids import normalize_for_member_match` in `_build_member_map`

`warmup_cache.py:135` does this lazy import inside the function body. After the split, `_build_member_map` STAYS in `warmup_cache.py` — the lazy import is unchanged. `ensure_legacy_paths()` already puts `SKILL_SCRIPTS_DIR` on sys.path, so `guidance_ids` resolves.

### 10.3 The lazy `from utils.market_session import MarketSessionClassifier` in `build_inter_quarter_context`

`warmup_cache.py:1509` (becoming `inter_quarter_context.py:<line>` after Stage 3.1) does this lazy import inside the function body. The `_paths.py` utils-shadow fix pins `sys.modules['utils']` at `_paths.ensure_legacy_paths()` time — which the new module also calls. So the lazy import resolves correctly. `test_builders_paths.py:118 test_utils_market_session_resolves_after_ensure_legacy_paths` still passes.

### 10.4 `_run_v2_regression_tests` references `_format_value` and `resolve_unit_groups` by name

In the original `warmup_cache.py` (lines 2017–2056), `_run_v2_regression_tests()` calls `_format_value(...)` and `resolve_unit_groups(...)` directly — those are module-local references. After moving the function into `guidance_history.py`, `_format_value` and `resolve_unit_groups` are ALSO in `guidance_history.py` (module-local in the new module too). The references resolve in the new module's namespace. NO edit to the function body required.

### 10.5 `sys.argv` parsing in `warmup_cache.main()`

`warmup_cache.main()` (lines 1882–2000) parses `sys.argv` for 8 modes. After the split, `main()` STAYS in `warmup_cache.py` — every mode's dispatcher (`run_warmup`, `run_transcript`, `run_mda`, `run_8k`, `build_8k_packet`, `build_guidance_history`, `build_inter_quarter_context`) is reachable via the warmup_cache namespace (either as a local def for extraction modes or as a re-exported binding for orchestration modes). NO edit to `main()` required.

### 10.6 `if __name__ == "__main__"` block at bottom of `warmup_cache.py`

**Verified (warmup_cache.py:2063–2066):**

```python
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        sys.exit(0 if _run_v2_regression_tests() else 1)
    main()
```

The `--test` branch dispatches the inline regression suite and exits BEFORE `main()`; for every other invocation `main()` IS called. So:

- `python -m scripts.earnings.builders.warmup_cache --test` → runs `_run_v2_regression_tests`, exits with the suite's pass/fail.
- `python -m scripts.earnings.builders.warmup_cache FIVE --8k-packet <ACC>` → falls through to `main()`, dispatches the `--8k-packet` mode. Stage 0 golden capture relies on this.
- `bash warmup_cache.sh --test` and `bash warmup_cache.sh FIVE --8k-packet <ACC>` both work via the skill shim's identical pre-dispatch.

After Stage 2.2, `_run_v2_regression_tests` resolves to the re-exported binding from `guidance_history` — same Python object, same exit code. NO edit to this block required after the cutover.

### 10.7 The `_paths.py` import line at the top of warmup_cache.py

```python
from ._paths import ensure_legacy_paths
ensure_legacy_paths()
```

UNCHANGED. The new domain modules add their own copies of these two lines. `ensure_legacy_paths()` is idempotent (verified by `test_builders_paths.py:test_ensure_legacy_paths_is_idempotent`), so calling it three more times is harmless.

### 10.8 Aggressive parallel imports under ThreadPoolExecutor

`earnings_orchestrator.py` runs all 7 builders in `ThreadPoolExecutor`. Each builder thread does `from scripts.earnings.builders.warmup_cache import build_X`. After the split, this triggers:

1. Python import lock acquired for `scripts.earnings.builders.warmup_cache`
2. warmup_cache module loads → executes `from .eight_k_packet import build_8k_packet` (and the other re-exports)
3. eight_k_packet loads → calls `ensure_legacy_paths()` (idempotent) → finishes
4. warmup_cache binding completes → import returns

All threads see the SAME warmup_cache module after step 4. The ThreadPoolExecutor's parallel calls compete for the import lock for FIRST import only; subsequent imports are O(1) hash lookups. `test_builders_imports.py:test_concurrent_imports_preserve_identity` (already exists from Stage 15 of the prior migration) covers this.

### 10.9 Don't tag `pre-warmup-split-main-before-merge` if the worktree branch isn't ready

The tag is created ONLY when ALL 10 commits are green and gates pass. If gates fail mid-stage, the worktree is the only place affected — main stays clean — so no tag needed.

### 10.10 If the worktree exists pre-flight

If `/home/faisal/em-warmup-cache-split` already exists, do NOT delete it without checking `git -C /home/faisal/em-warmup-cache-split status` — it may contain in-progress work. Ask the user before removing.

### 10.11 If `git status` shows unintended main edits during stages

Per §0 hygiene: `git status -s -- <fenced files>` after every commit should return empty. If it returns non-empty, STOP and ask the user. The most likely cause is editing main accidentally (forgot to `cd` into worktree). Do NOT auto-revert.

### 10.12 If the venv path differs

The plan assumes `PY=/home/faisal/EventMarketDB/venv/bin/python`. Test files use `PY = sys.executable`. If the executor invokes pytest from a different interpreter, `sys.executable` reflects that. Both paths should resolve the same packages because the worktree shares the main repo's `venv/` (the venv is gitignored — the worktree dir does NOT have its own venv).

### 10.13 If extraction-worker scales up mid-merge

Scaled-up worker pods read the orchestrator code from the hostPath mount of `/home/faisal/EventMarketDB`. If they boot during a `--ff-only` merge (which rewrites files atomically per file but NOT atomically across files), they could see a partially-applied state. Mitigation: §9.1 quiescence check. If a pod boots between merge and re-gate, kill it (`kubectl delete pod -n processing <pod>`); KEDA will rebuild against the merged code.

### 10.14 If the pre-existing `--test` pass count changes

The Stage 0 baseline capture (§6.3) records the `--test` exit-code summary (`X passed, 0 failed out of X`). After the split, the number `X` MUST be unchanged (the same internal regression suite runs from `guidance_history._run_v2_regression_tests`). If it changes, something was lost in the move. Diff the suite content vs. the pre-flight capture.

### 10.15 The `Counter`/`defaultdict` removal can be missed

`warmup_cache.py`'s top-level imports include `from collections import Counter, defaultdict`. After Stage 5, neither is used. The Stage 5 gate's import-clean check now hard-asserts on all three forbidden imports (`math`, `collections.Counter`, `collections.defaultdict`) — see Stage 5 Gate step 1.

### 10.16 Mock-patch precedence asymmetry (subtle Python semantics — read before writing tests)

`from X import Y as Z` snapshots the binding `X.Y` into the importer's `__dict__` AT IMPORT TIME. After import, `importer.Y` is a reference to the SAME object that `X.Y` was at that moment. **If you later do `mock.patch("X.Y", ...)`, you rebind `X.__dict__["Y"]` ONLY — `importer.__dict__["Y"]` keeps pointing at the ORIGINAL object.**

Concrete consequences for this plan:

- Inside `warmup_cache.py`, `run_8k` calls `_fetch_8k_core(...)` unqualified. The body does `wc.run_8k.__globals__["_fetch_8k_core"]` lookup against `warmup_cache.__dict__`. After Stage 1.2, that dict entry is the canonical `eight_k_packet._fetch_8k_core` object (via `from .eight_k_packet import _fetch_8k_core`). To mock `_fetch_8k_core` for a `run_8k` test, you MUST patch `scripts.earnings.builders.warmup_cache._fetch_8k_core` — patching `eight_k_packet._fetch_8k_core` does NOT take effect because it doesn't reach into warmup_cache's dict.
- Same rule for `get_manager`: `run_8k` looks it up in `wc.__dict__`, so mocks must patch `wc.get_manager`.
- For `eight_k_packet.build_8k_packet`, the function lives in eight_k_packet, so `build_8k_packet.__globals__` IS `eight_k_packet.__dict__`. Mocks of `get_manager` for build_8k_packet tests should patch `eight_k_packet.get_manager`.

**Rule of thumb:** patch the namespace WHERE the function being CALLED is DEFINED.

- `wc.run_8k(...)` → patch `wc.X` (warmup_cache's namespace)
- `ek.build_8k_packet(...)` → patch `ek.X` (eight_k_packet's namespace)

For pure identity assertion (`wc._fetch_8k_core is ek._fetch_8k_core`), no patch is needed. The verification of `wc.run_8k.__globals__["_fetch_8k_core"] is ek._fetch_8k_core` is a stronger form of the same identity check.

### 10.17 Do NOT add `__all__` to `warmup_cache.py`

Currently `warmup_cache.py` has NO module-level `__all__`. The `.claude/skills/.../warmup_cache.py` skill shim relies on `dir(_impl)` (where `_impl` is `scripts.earnings.builders.warmup_cache`) to discover and re-export every non-dunder name. If a future maintainer adds an `__all__` to `warmup_cache.py` to "tidy up the public surface", `dir()` is unaffected and the shim continues to work — BUT `from warmup_cache import *` would silently change semantics (only `__all__`'s entries flow through), and any caller doing `*`-import on the facade would lose access to private re-exports. The plan's invariant is to leave `__all__` ABSENT from `warmup_cache.py` to preserve the existing shim+wildcard contract.

### 10.18 No-cross-domain-imports static guard (defensive future-proofing)

The 3 domain modules `eight_k_packet.py`, `guidance_history.py`, `inter_quarter_context.py` are PEERS — none imports another. A future maintainer might add `from .guidance_history import _format_value` to `inter_quarter_context.py` for some refactoring, creating silent coupling that breaks the facade-only contract.

The plan adds `test_no_cross_domain_imports` to `test_builders_warmup_split.py` (alongside `test_no_warmup_cache_back_imports`):

```python
def test_no_cross_domain_imports():
    """Domain modules MUST be peers — none imports another. Cross-imports
    create silent coupling that bypasses the facade-only contract."""
    targets = ["eight_k_packet", "guidance_history", "inter_quarter_context"]
    for me in targets:
        path = REPO / f"scripts/earnings/builders/{me}.py"
        if not path.exists():
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    for other in targets:
                        if other != me and other in node.module:
                            pytest.fail(
                                f"{me}.py imports from {node.module} — domain "
                                f"modules must be peers; share via warmup_cache facade only"
                            )
                # Also catch `from . import guidance_history`-style alias imports
                for alias in node.names:
                    for other in targets:
                        if other != me and alias.name == other:
                            pytest.fail(
                                f"{me}.py imports name '{alias.name}' — domain "
                                f"modules must be peers; share via warmup_cache facade only"
                            )
```

Add this in Stage 0 alongside `test_no_warmup_cache_back_imports`.

---

## 11. Aggregate Risk Table

| Stage | Files touched | Identity preserved? | --test green? | Goldens green? | Reversibility |
|---|---|---|---|---|---|
| 0 | +1 test, +3 fixtures | N/A (no relocation) | YES | N/A (skipped) | `git revert HEAD` |
| 1.1 | +1 module, +1 test | N/A (def in both places) | YES | YES (skipped) | `git revert HEAD` |
| 1.2 | -2 fns, -5 queries from warmup_cache; +re-export block; +stand-alone identity test in test_builders_imports.py (NO EXPECTED_SURFACE / MODULE_PAIRS edits) | YES (facade matches eight_k_packet) | YES | YES (skipped) | `git revert HEAD` (restores defs to warmup_cache; eight_k_packet stays as additive copy) |
| 2.1 | +1 module, +1 test | N/A | YES (1 def per place) | YES (skipped) | `git revert HEAD` |
| 2.2 | -10 symbols from warmup_cache; +re-export block; +stand-alone identity test in test_builders_imports.py (NO EXPECTED_SURFACE / MODULE_PAIRS edits) | YES (facade matches guidance_history) | YES (re-exported _run_v2_regression_tests) | YES (skipped) | `git revert HEAD` |
| 3.1 | +1 module, +1 test, +shadow guard | N/A | YES | YES (skipped) | `git revert HEAD` |
| 3.2 | -25 symbols from warmup_cache; +re-export block; +stand-alone identity test (NO EXPECTED_SURFACE / MODULE_PAIRS edits); ++shadow guard | YES (facade matches inter_quarter_context, _parse_dt_for_pit shadow holds) | YES | YES (skipped) | `git revert HEAD` |
| 4 | adapters.py: 3 lazy import paths updated; test patch target updated | YES (canonical via different path, same object) | YES | YES (skipped) | `git revert HEAD` |
| 5 | warmup_cache.py: imports cleaned, docstring refreshed | YES (Stage-5 static guard activates intrinsically — no marker file) | YES | YES (live) | `git revert HEAD` |
| 6 | README.md only | N/A | YES | YES | `git revert HEAD` |

### 11.1 Acceptance Bar (one-paragraph close)

The split is done only when `warmup_cache.py` is a facade, the three builders live in separate canonical modules, all old import paths still work, all 4-path identity tests pass (`facade is canonical`), the `_parse_dt_for_pit` shadow holds (`warmup is not peer`), the static "no-redefine" guard passes, the renderer goldens stay green by both count AND test names, the 8-K / guidance / inter-quarter structural-equality goldens for FIVE PASS (a Neo4j-unavailable skip is NOT green — require either successful re-run with Neo4j up, or an explicit user-approved waiver recorded in the PR description), and live validation (`test_builder_validation.py --ticker FIVE` and `test_adapter_validation.py --ticker FIVE`) PASSES or has the same explicit waiver. If any of these is red, STOP and rollback per §9.7.

---

**Cumulative residual risk: practically zero.** Justification:

- Every relocated symbol identity is asserted in EVERY post-cutover gate.
- The `warmup_cache.py` → `<domain>` re-export is purely additive in Python's import semantics — `from .X import Y` binds `Y` into the importer's namespace at the SAME object id.
- No external caller updates imports. Existing test suite (~165 tests) catches any divergence.
- Each commit is independently revertible.
- ff-merge with pre-merge tag enables tag-based revert across the entire range without history rewrite.

---

## 12. Done Criteria (24 checkboxes)

- [ ] Pre-flight checks 6.1–6.6 all pass
- [ ] Worktree created at `/home/faisal/em-warmup-cache-split`
- [ ] Stage 0 commit lands; gate green
- [ ] Stage 1.1 commit lands; gate green; eight_k_packet imports OK
- [ ] Stage 1.2 commit lands; gate green; facade-vs-canonical identity holds for 7 symbols
- [ ] Stage 2.1 commit lands; gate green; guidance_history imports OK; inline `_run_v2_regression_tests()` returns True
- [ ] Stage 2.2 commit lands; gate green; facade-vs-canonical identity holds for 10 symbols; --test green via every CLI path
- [ ] Stage 3.1 commit lands; gate green; inter_quarter_context imports OK; _parse_dt_for_pit distinct from peer
- [ ] Stage 3.2 commit lands; gate green; facade-vs-canonical identity holds for 25 symbols; extended shadow guard passes
- [ ] Stage 4 commit lands; gate green; adapters point at canonical domain modules
- [ ] Stage 5 commit lands; gate green; warmup_cache.py is < 800 lines (target ~520); imports cleaned; static no-redefine guard passes; goldens structurally-equal
- [ ] Stage 6 commit lands; README updated
- [ ] Total commit count: 10 (Stage 4 confirmed included)
- [ ] Pre-merge production quiescence (Redis queue empty, no extraction-worker pods)
- [ ] `git tag pre-warmup-split-main-before-merge` applied to main HEAD BEFORE merge
- [ ] `git merge --ff-only warmup-cache-domain-split` succeeds (no merge commit)
- [ ] Post-merge gate on main: full builders test matrix green
- [ ] Post-merge gate: orchestrator --test 9/9
- [ ] Post-merge gate: `warmup_cache.sh --test` green
- [ ] Post-merge gate: `/home/faisal/EventMarketDB/venv/bin/python -m scripts.earnings.builders.warmup_cache --test` green (venv interpreter required — system `python3` lacks `neo4j`)
- [ ] Live golden gate via `pytest -m live` on `test_builders_warmup_split.py` green (REQUIRED — a Neo4j-unavailable skip does NOT satisfy this; record explicit user-approved waiver if connectivity blocked)
- [ ] Live `test_builder_validation.py --ticker FIVE` AND `test_adapter_validation.py --ticker FIVE` both green (REQUIRED — both run in §9.4 post-merge gate; a Neo4j-unavailable skip is not green; record explicit user-approved waiver if connectivity blocked)
- [ ] Worktree removed; branch deleted
- [ ] (Optional) `git push origin main` + `git push origin pre-warmup-split-main-before-merge`

---

## 13. Review Pass Checklist

Before submitting the final commit ledger, run these review passes:

**Pass 0 (test code itself can have bugs):** Hand-audit `test_builders_warmup_split.py`. Ensure every parametrize entry maps to a real symbol in the new module. Verify the `pytest.skip(...)` guards fire only when the corresponding domain module is absent — NOT when the test discovers a real failure. Verify `_strip_volatile` only strips `assembled_at` (not e.g. `pit` or other meaningful fields).

**Pass 1 (import surface):** `rg -n "from warmup_cache import\|from scripts.earnings.builders.warmup_cache import"` across the whole repo. Every hit MUST still resolve correctly via the facade re-export. No hit should require a caller update.

**Pass 2 (CLI surface):** Run all 8 CLI modes manually against ticker FIVE:

```bash
set -euo pipefail
cd /home/faisal/em-warmup-cache-split   # or main repo root post-merge
PY=/home/faisal/EventMarketDB/venv/bin/python

# CRITICAL: live CLI commands need Neo4j env vars — neograph.get_manager() reads
# os.getenv("NEO4J_URI") directly and does NOT load .env. Without this, the first
# live command fails with: ConnectionError: URI scheme b'' is not supported.
set -a; source .env; set +a

PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache FIVE
# Use the verified FIVE fixture from test_builder_validation.py:58-71 (also referenced
# in Stage 0). All values are concrete — do NOT guess.
ACC=0001177609-25-000037
FILED=2025-08-27T16:14:48-04:00
PREV=2025-06-04T16:23:39-04:00
# TID = a current FIVE transcript id; auto-capture below.
TID=$(PYTHONPATH=scripts/earnings $PY -c "from neograph.Neo4jConnection import get_manager; m=get_manager(); rows=m.execute_cypher_query_all('MATCH (t:Transcript)-[:FOR_COMPANY]->(c:Company {ticker:\"FIVE\"}) RETURN t.id AS id LIMIT 1', {}); print(rows[0]['id']); m.close()")
echo "captured TID=$TID"
PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache FIVE --transcript "$TID"
# Pass 2 is a CLI dispatch smoke test — empty MD&A response is acceptable (the
# point is "did the dispatcher route --mda correctly", not "did Neo4j return data").
# Live goldens cover data correctness; mocked unit tests cover query-routing correctness.
PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache FIVE --mda "$ACC"
PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache FIVE --8k "$ACC"
PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache FIVE --8k-packet "$ACC"
PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache FIVE --guidance-history --pit "$FILED"
PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache FIVE --inter-quarter --prev-8k "$PREV" --context-cutoff "$FILED"
PYTHONPATH=scripts/earnings $PY -m scripts.earnings.builders.warmup_cache --test
```

(Note: every mode above works via `python -m scripts.earnings.builders.warmup_cache` because the `__main__` block falls through to `main()` when `--test` is absent — verified §10.6. The `.claude/skills/.../warmup_cache.py` shim and `warmup_cache.sh` are equivalent CLI entry points.)

**Pass 3 (behavioral equivalence):** Live structural-equality goldens (auto-activated by `_all_cutovers_complete()` intrinsic check). If any fails, identity isn't enough — the function body must have drifted during the move.

**Pass 4 (production safety):** Quiescence check before merge; post-merge worker-pod sanity check.

---

## 14. Non-Regression Guarantees

After all 10 commits land and ff-merge completes:

1. `from warmup_cache import build_8k_packet` (bare) returns the canonical `eight_k_packet.build_8k_packet` object.
2. `from scripts.earnings.builders.warmup_cache import build_8k_packet` (qualified) returns the same object.
3. `from scripts.earnings.builders.eight_k_packet import build_8k_packet` (canonical) returns the same object.
4. `from scripts.earnings.builders import build_8k_packet` (package root, via `__init__.py` → `adapters.py` → lazy import) returns the adapter wrapper, which lazy-imports the canonical domain module (Stage 4 is REQUIRED — adapter chain points at `eight_k_packet` directly, not via the warmup_cache facade hop). Adapter wrapper identity unchanged.
5. Same triple for `build_guidance_history`, `build_inter_quarter_context`, `render_guidance_text`, `render_inter_quarter_text`, `_parse_dt_for_pit`, `_run_v2_regression_tests`, `_fetch_8k_core`, every helper, every query constant.
6. `_parse_dt_for_pit` from `warmup_cache` and `inter_quarter_context` is the SAME object; it is NOT the same object as `peer_earnings_snapshot._parse_dt_for_pit`.
7. `bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh --test` exits 0 with the same `passed` count.
8. `/home/faisal/EventMarketDB/venv/bin/python .claude/skills/earnings-orchestrator/scripts/warmup_cache.py --test` exits 0 with the same `passed` count (venv interpreter required — system `python3` lacks `neo4j` and would ImportError at module-load).
9. `/home/faisal/EventMarketDB/venv/bin/python -m scripts.earnings.builders.warmup_cache --test` (or `$PY -m ...` where `$PY` points at the venv) exits 0 with the same `passed` count. Raw system `python3` would ImportError on `neo4j`.
10. Orchestrator runs all 7 builders in parallel; all return successful packets; rendered bundle structurally equal (Python dict `==` after `json.loads`, modulo `assembled_at`). Verified by `earnings_orchestrator.py --test` + `test_builder_validation.py --ticker FIVE` + `test_adapter_validation.py --ticker FIVE`.
11. The `if __name__ == "__main__"` block in `warmup_cache.py` continues to dispatch `--test` via the re-exported `_run_v2_regression_tests`.
12. `warmup_cache.sh` is unchanged (still execs the skill shim).
13. The `EXPECTED_SURFACE` test continues to pass for the unchanged `warmup_cache` row (NO new rows added — per §2.3 plan decision; per-domain surface lives in `test_builders_warmup_split.py` parametrize lists instead).
14. The `MODULE_PAIRS` 4-path identity test continues to pass for every existing row.
15. The static AST shim guard (`test_builders_static.py`) is unchanged — `warmup_cache.py` and the new domain modules are NOT shims; they're real implementation files.
16. No K8s, KEDA, Docker, .env, or CI change.

These 16 guarantees are the contract. If any one fails post-merge, rollback per §9.7.

---

## 15. Quick Reference for Future Maintainers

- **Want to change `build_8k_packet` behavior?** Edit `scripts/earnings/builders/eight_k_packet.py`. The change propagates to every caller via re-export — no other file needs editing.
- **Want to add a new query constant for the 8-K builder?** Add it to `eight_k_packet.py` AND to the `from .eight_k_packet import (...)` block in `warmup_cache.py` if it should be reachable via the warmup_cache namespace (most should — for symmetry and to satisfy the `EXPECTED_SURFACE` test if you add one there too).
- **Want to add a new IQ helper?** Same pattern — define in `inter_quarter_context.py`, re-export in `warmup_cache.py` if external code needs it.
- **Want to add a new CLI mode?** Edit `warmup_cache.main()`. New mode dispatchers can call any function reachable via `warmup_cache.X` (extraction-side or re-exported orchestration).
- **Want to add a new orchestration domain module?** Create `scripts/earnings/builders/<X>.py` matching the eight_k_packet/guidance_history/inter_quarter_context shape. Add re-exports to `warmup_cache.py`. Add a parametrize list for it in `test_builders_warmup_split.py` (mirrors `_EIGHTK_SYMBOLS` etc.) and a stand-alone facade-vs-canonical identity test in `test_builders_imports.py`. Do NOT add the new module to `EXPECTED_SURFACE` — it's bare-import-keyed (see §2.3). Update `adapters.py` if it's a new orchestration builder.
- **Identity test fails?** Someone replaced a `from .X import Y` re-export with a wrapper function `def Y(...): return _impl(...)` somewhere in `warmup_cache.py`. Fix: restore direct re-export.
- **Static "no-redefine" test fails?** Someone added a `def build_8k_packet` (or other relocated function) directly into `warmup_cache.py`. Fix: remove the def and rely on the re-export.
- **`--test` count drops?** Someone removed test cases from `_run_v2_regression_tests` in `guidance_history.py`. Compare against the Stage 0 baseline.

---

## 16. Out-of-Scope Refusals (do NOT bundle into this PR)

1. Don't move `run_warmup`, `run_transcript`, `run_mda`, `run_8k` out of `warmup_cache.py`. They're extraction-side, not orchestration. The split is for ORCHESTRATION builders only.
2. Don't delete `_fetch_8k_core` from `warmup_cache.py`'s back-compat surface — it's needed by `run_8k`. (It's relocated to `eight_k_packet.py` but re-exported.)
3. Don't merge `_parse_dt_for_pit` with `peer_earnings_snapshot._parse_dt_for_pit`. Same name, different functions, intentional.
4. Don't restructure the `if __name__ == "__main__"` pre-dispatch in `warmup_cache.py`. The `--test`-then-`main()` pattern is correct as-is (verified §10.6) and is mirrored by the `.claude` skill shim — a restructure would silently desync the two CLI entry points.
5. Don't update `.claude/plans/planner.md`, `plannerStep5.md`, `earnings-orchestrator.md` — they reference helpers by name in prose that remains accurate.
6. Don't update `.claude/references/prediction_context_bundle.md` — its debug one-liners use `from builder_adapters import X` which still works through the unchanged adapter shim.
7. Don't change schemas, packet shapes, atomic-write semantics, `/tmp/...json` output paths, default `out_path`, retry policy, source policy, or any rendered-text format.
8. Don't modify the `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py` skill shim or `warmup_cache.sh` shell wrapper.
9. Don't modify `scripts/earnings/utils.py` (the file that previously needed the utils-shadow fix in `_paths.py` — this plan does not touch `_paths.py`).
10. Don't touch K8s manifests, KEDA scalers, Docker images, or `.env`.
11. Don't add CI, coverage, or new dependencies.
12. Don't rename any function, class, query constant, or helper.
13. Don't run `live` tests as PER-STAGE gates. They ARE required as the final pre-merge or post-merge validation (NOT optional — a Neo4j-unavailable skip is not green; record an explicit user-approved waiver if connectivity is blocked).
