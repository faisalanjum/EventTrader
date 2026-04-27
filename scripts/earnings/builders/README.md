# scripts/earnings/builders — canonical builder package

This subpackage was created on 2026-04-26 by relocating 6 builder files into
a single folder for cleaner future refactoring. See
`.claude/plans/builders_restructure.md` for the full move plan and
TDD-driven safety invariants.

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

## Shim contract

There is a permanent compatibility shim at every OLD path. **DO NOT delete:**

- `scripts/earnings/builder_adapters.py` (module-only shim — no `__main__`)
- `scripts/earnings/build_consensus.py` (CLI shim with PEP 562 `__getattr__`/`__dir__` for `_classifier` mutable forwarding)
- `scripts/earnings/build_prior_financials.py` (CLI shim)
- `scripts/earnings/macro_snapshot.py` (CLI shim)
- `scripts/earnings/peer_earnings_snapshot.py` (CLI shim)
- `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py` (CLI shim, also script-target for `warmup_cache.sh`)

Each shim does the two-step pattern:

```python
from scripts.earnings.builders import <module> as _impl

# Step 1: bind every non-dunder name to shim globals so `from <shim> import _priv` works
for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

# Step 2: __all__ public-only so `from <shim> import *` matches old wildcard semantics
__all__ = [_name for _name in dir(_impl) if not _name.startswith("_")]
del _name
```

`build_consensus.py` additionally defines `__getattr__` and `__dir__` (PEP 562)
to forward mutable globals like `_classifier` (the lazy
`MarketSessionClassifier` singleton) — eager-copy can't track post-import
mutations. See `test_classifier_singleton_attribute_access_across_paths` and
`test_classifier_appears_in_dir_across_paths` for the regression guards.

## Identity invariant

`scripts/earnings/test_builders_imports.py` is the **load-bearing regression
guard**. It enforces that every relocated symbol resolves to the SAME function
object via Python `is` from EVERY import path:

1. Old bare path     — `from build_consensus import build_consensus` (works because callers `sys.path.insert(0, scripts/earnings)`)
2. Old qualified path — `from scripts.earnings.build_consensus import build_consensus`
3. New canonical path — `from scripts.earnings.builders.consensus import build_consensus`
4. Package root       — `from scripts.earnings.builders import build_consensus`

If any test in this file fails, identity has been broken — revert and
investigate. The current MODULE_PAIRS covers 42 (symbol, module) pairs across
6 builder modules.

## Static shim guard

`scripts/earnings/test_builders_static.py` asserts that old shim files contain
NO `FunctionDef` (except PEP 562 hooks `__getattr__` and `__dir__`) or
`ClassDef` AST nodes. This is the permanent guard against accidentally
re-introducing logic into a shim file.

## Path discipline (`_paths.py`)

`_paths.ensure_legacy_paths()` is the single source of truth for sys.path
setup. Every canonical builder calls it once at top-of-file:

```python
from ._paths import ensure_legacy_paths
ensure_legacy_paths()
```

It inserts (in this precedence order, highest precedence first):

1. `SKILL_SCRIPTS_DIR` = `<repo>/.claude/skills/earnings-orchestrator/scripts`
2. `EARNINGS_DIR` = `<repo>/scripts/earnings`
3. `SCRIPTS_DIR` = `<repo>/scripts`
4. `REPO_ROOT` = `<repo>`

Plus a surgical fix: pins `sys.modules['utils']` to the repo-root `utils/`
package via `importlib.util.spec_from_file_location` to prevent
`scripts/earnings/utils.py` (a single FILE) from shadowing the `utils/`
package under the precedence above. See `_paths.py` docstring for details.

## Adding a new builder

1. Add the module to `builders/`.
2. If the underlying function should be exposed by `adapters.py`, add it there.
3. If callers should be able to import from `scripts.earnings.builders` directly,
   re-export in `__init__.py` and add to `__all__`.
4. Add a row to `EXPECTED_SURFACE` in `test_builders_surface.py`.
5. Add a row to `MODULE_PAIRS` in `test_builders_imports.py` (or skip if no
   shim needed at an old path).
6. (No shim needed — the file lives in the canonical location from day one.)

## Test surface

| Test file | Count | What it asserts |
|---|---|---|
| `test_builders_paths.py` | 12 | `_paths.py` API, idempotence, precedence, fresh-subprocess `utils.market_session` resolution, fresh-subprocess lazy-import resolution |
| `test_builders_surface.py` | 12 | Public + private cross-export symbols are reachable on every module |
| `test_builders_imports.py` | 81+12skip | 4-path identity for every (symbol, module) in MODULE_PAIRS + named guards (singleton, attribute-access, dir, shadow, xbrl-lazy, package-root, completeness, concurrent) |
| `test_builders_static.py` | 29 | AST-level: shim files contain no business logic; CLI shims have `__main__`; `__all__` excludes underscore names |
| `test_builders_*.py` (per-builder mocked) | 28 | Per-builder unit tests with mocked Neo4j / yfinance / AV |
| `test_builders_cli_smoke.py` | 6 (2 non-live, 4 live) | warmup_cache `--test` (CLI + .sh wrapper) — non-live; build_* CLIs — live |
| `test_builders_warmup_split.py` | ~50 | Pre-/post-split goldens (FIVE), facade-vs-canonical identity per symbol per domain, no-back-imports static check |
| `test_builders_eight_k_packet.py` | ~11 | Mocked: ValueError on missing meta, items JSON parse, null stripping, exhibit preview diff, filing text fallback, atomic write, manager.close on success+exception |
| `test_builders_guidance_history.py` | ~18 | Mocked: empty packet, PIT vs live query, unit remap, dup collapse (numeric + qualitative), source priority, richest selection, member union/sort, series sort, _format_value edges, render header/cutoff |
| `test_builders_inter_quarter_context.py` | ~40 | Mocked: boundary roles, PIT-safe price gating, fallback context, synthetic days, forward-return nulling, JSON parse fallback, NaN/list normalization, event sort, sig+gap rules, summary counts, render branches, _parse_dt_for_pit format coverage |

Total non-live: **285 tests** post-warmup_cache 3-domain split (was 165 pre-split; +120 from `test_builders_warmup_split.py` ~50, `test_builders_eight_k_packet.py` ~11, `test_builders_guidance_history.py` ~18, `test_builders_inter_quarter_context.py` ~40).
