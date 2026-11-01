# Builders Package Restructure — Unified Zero-Regression Migration Plan

**Status:** PLANNING ONLY. No implementation has been done from this plan yet.
**Date prepared:** 2026-04-25
**Branch:** `builders-restructure`
**Worktree:** `/home/faisal/em-builders-restructure`
**Total commits: 20 required** (Stage 0 = 4, Stage 1 = 1, Stages 2–13 = 12, Stage 14 = 1, Stage 15 = 1, Stage 16 README = 1). Stage 16 README is **mandatory** — it is zero-risk and useful for future maintainers.

**Primary goal:** move the real earnings bundle builder implementations into a dedicated package under `scripts/earnings/builders/` while preserving every existing import path, CLI entrypoint, shell wrapper, and production behavior.

**Non-negotiable safety rule:** old paths remain permanent compatibility shims. This migration must never require an external caller to switch imports in the same PR.

**Aggregate risk:** practically zero — combining the safest elements from two independently-derived plans:
- Centralized `_paths.py` module (no scattered `parents[N]` math)
- Two-step copy-then-shim per file (production never sees a "moved-but-no-shim" state)
- TDD-first foundation (regression-guard tests written BEFORE any move)
- Static AST verification (proves shim files are shim-only)
- 4-path identity invariant (every relocated symbol resolves to the same Python object via `is` from every import path)
- Per-builder mocked unit tests (deterministic, no live-service dependencies)
- Three explicit risk-specific identity guards (singleton, cross-module shadow, lazy import)
- Worktree isolation + ff-merge during documented production-quiescence window

---

## 1. Executive Decision

Do the migration. Stage it as additive copy commits followed by separate shim swap commits, with permanent compatibility shims at every old path.

**Do not do it as a simple file move.** A simple move is unsafe because the current system has:

- Direct old-path imports from tests, scripts, sidecars, docs, and debug tools
- Direct CLI usage of old file paths
- Skill-agent shell usage of `.claude/skills/earnings-orchestrator/scripts/warmup_cache.sh`
- Builder code that depends on `Path(__file__).resolve().parents[2]`
- Bare imports made possible only by `sys.path` manipulation
- Live dependencies on Neo4j, Redis, Alpha Vantage, Polygon, Yahoo, Benzinga, and `/tmp` packet files

### Target design

```text
scripts/earnings/
  builder_adapters.py                  # permanent old-path import shim; module-only, no CLI contract
  build_consensus.py                   # permanent old-path import + CLI shim
  build_prior_financials.py            # permanent old-path import + CLI shim
  macro_snapshot.py                    # permanent old-path import + CLI shim
  peer_earnings_snapshot.py            # permanent old-path import + CLI shim
  builders/
    __init__.py                        # canonical public builder package — re-exports 7 adapter functions
    _paths.py                          # repo-root + sys.path helpers (the load-bearing centralization)
    adapters.py                        # canonical adapter implementation
    consensus.py                       # canonical build_consensus implementation
    prior_financials.py                # canonical build_prior_financials implementation
    macro_snapshot.py                  # canonical build_macro_snapshot implementation
    peer_earnings_snapshot.py          # canonical build_peer_earnings_snapshot implementation
    warmup_cache.py                    # canonical 8K + guidance + inter-quarter implementation
    README.md                          # layout + shim contract documentation (Stage 16, MANDATORY)

.claude/skills/earnings-orchestrator/scripts/
  warmup_cache.py                      # permanent old-path import + CLI shim
  warmup_cache.sh                      # unchanged; still calls old warmup_cache.py path
```

Final state must have **one canonical implementation per builder**. Old top-level files must contain only shim code, not copied business logic.

### Naming rationale (drops `build_` prefix inside the package)

Inside the package, `from scripts.earnings.builders.consensus import build_consensus` is clearer than the redundant `from scripts.earnings.builders.build_consensus import build_consensus`. The function name (`build_consensus`) is unchanged — only the file name drops the prefix. The shim files at OLD paths keep their original names (`build_consensus.py`, `build_prior_financials.py`) so external callers' bare imports keep working unchanged.

`adapters.py` (no leading underscore) because the adapter module is the canonical public-API shape; `_adapters.py` would falsely signal "private". The 7 adapter functions are re-exported at package root via `__init__.py`.

---

## 2. Current-State Facts Verified Against The Repo

The migration scope is about 6,602 lines, not a tiny cleanup:

```text
1103 scripts/earnings/build_consensus.py
1763 scripts/earnings/build_prior_financials.py
 863 scripts/earnings/macro_snapshot.py
 460 scripts/earnings/peer_earnings_snapshot.py
 347 scripts/earnings/builder_adapters.py
2066 .claude/skills/earnings-orchestrator/scripts/warmup_cache.py
```

Tracked files in direct scope:

```text
scripts/earnings/build_consensus.py
scripts/earnings/build_prior_financials.py
scripts/earnings/macro_snapshot.py
scripts/earnings/peer_earnings_snapshot.py
scripts/earnings/builder_adapters.py
.claude/skills/earnings-orchestrator/scripts/warmup_cache.py
.claude/skills/earnings-orchestrator/scripts/warmup_cache.sh
```

There is no `scripts/__init__.py` and no `scripts/earnings/__init__.py`. That is acceptable because `scripts.earnings.renderer` already works as a namespace package. **Do not add either file in this PR**; adding package initializers is unrelated and could change import behavior.

### Current orchestrator imports

```python
from builder_adapters import (
    build_8k_packet,
    build_guidance_history,
    build_inter_quarter_context,
    build_peer_earnings_snapshot,
    build_macro_snapshot,
    build_consensus,
    build_prior_financials,
)
```

### Current adapter imports (lazy, inside functions)

```python
from warmup_cache import build_8k_packet as _legacy
from warmup_cache import build_guidance_history as _legacy
from warmup_cache import build_inter_quarter_context as _legacy
from peer_earnings_snapshot import build_peer_earnings_snapshot as _legacy
from macro_snapshot import build_macro_snapshot as _legacy
from build_consensus import build_consensus as _legacy
from build_prior_financials import build_prior_financials as _legacy
```

### Direct old-path consumers

```text
scripts/earnings/earnings_orchestrator.py
scripts/earnings/render_section.py
scripts/earnings/compare_section.py
scripts/earnings/test_builder_validation.py
scripts/earnings/test_adapter_validation.py
scripts/earnings/test_build_prior_financials_regression.py
scripts/earnings/test_revenue_splits_integration.py
scripts/earnings/concept_fallback_discovery.py
scripts/earnings/q4_derivation.py
scripts/earnings/xbrl_exact_splits.py    # only doc-comment references; not actual imports
.claude/references/prediction_context_bundle.md
.claude/skills/extract/types/guidance/*.md
.claude/skills/earnings-orchestrator/scripts/warmup_cache.sh
```

### Critical private helpers imported externally

```text
from warmup_cache import _parse_dt_for_pit              # test_builder_validation.py:602
from peer_earnings_snapshot import _parse_dt_for_pit    # test_builder_validation.py:623
from build_prior_financials import classify_period      # q4_derivation.py:32, concept_fallback_discovery.py
from build_prior_financials import is_target_period     # q4_derivation.py:32, concept_fallback_discovery.py
from build_prior_financials import _parse_value         # concept_fallback_discovery.py:605
import build_prior_financials as bpf                    # test_build_prior_financials_regression.py
```

Therefore shims must re-export private single-underscore symbols too. A simple `from module import *` is insufficient because Python star import excludes underscore names unless the module defines `__all__`. The shim mechanism (full template in §5) does TWO things at module load:

1. **Bind every non-dunder name to the shim's globals** via a `for _name in dir(_impl): ... globals()[_name] = ...` loop. This makes BOTH public AND private names directly importable (e.g. `from build_prior_financials import _parse_value` works).
2. **Set `__all__` to PUBLIC names only** (no leading underscore). This preserves the original module's `from <module> import *` semantics — the original modules have no `__all__`, so `import *` defaults to public-only; the shim must match that to avoid silently leaking private helpers via wildcard.

Result: direct underscore imports work; wildcard imports stay scoped to public names; identity is preserved across all paths.

### Module-level mutable state

ONE concerning case: `build_consensus._classifier` (line 131) — a module-level `None` initialized lazily by `_get_classifier()`. If the module loads under TWO module names, Python creates two module objects, each with its own `_classifier` cell, splitting the singleton. **Mitigated by:** (a) zero external callers import `_classifier` directly (verified by grep); (b) explicit Stage 7 identity test asserts `_get_classifier()` returns the same object across all import paths.

### `_parse_dt_for_pit` shadowing

Two distinct functions of the same name in `warmup_cache` and `peer_earnings_snapshot`. The Stage 11 `test_parse_dt_for_pit_disambiguation` guard explicitly asserts they remain DIFFERENT objects across the move. Cross-contamination cannot happen if shim tables namespace each by qualified module.

---

## 3. Migration Scope

### In scope

- Move canonical implementation of `builder_adapters.py` to `scripts/earnings/builders/adapters.py`
- Move canonical implementation of `build_consensus.py` to `scripts/earnings/builders/consensus.py`
- Move canonical implementation of `build_prior_financials.py` to `scripts/earnings/builders/prior_financials.py`
- Move canonical implementation of `macro_snapshot.py` to `scripts/earnings/builders/macro_snapshot.py`
- Move canonical implementation of `peer_earnings_snapshot.py` to `scripts/earnings/builders/peer_earnings_snapshot.py`
- Move canonical implementation of `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py` to `scripts/earnings/builders/warmup_cache.py`
- Add `scripts/earnings/builders/_paths.py` for centralized path helpers
- Leave all old import paths and old CLI paths working via permanent shims
- Update orchestrator/debug-tool imports to canonical package after identity tests prove old and new paths are equivalent
- Add tests that prove import identity, CLI compatibility, static real-code location, normalized behavioral equivalence, and per-builder mocked unit behavior

### Out of scope

- **Do not split `warmup_cache.py` internally** into `eightk.py`, `guidance.py`, and `inter_quarter.py` in this PR. Move it as one canonical module first
- **Do not change builder behavior**, schemas, packet contents, default output paths, stderr/stdout behavior, retry behavior, source policy, or live/PIT rules
- **Do not change `warmup_cache.sh` behavior** except comments if needed
- **Do not migrate docs broadly** except the plan file and narrow path notes required to avoid future confusion
- **Do not remove old top-level files** — every old path is a permanent shim
- **Do not add CI**, coverage tooling, dependency changes, or Docker changes
- **Do not modify any `test_*.py` file's import style** — tests stay on bare imports (they ARE the regression coverage of the shim layer)
- **Do not consolidate the two `_parse_dt_for_pit` functions** — same name, different implementations is intentional today
- **Do not rename any function, class, or constant** inside the moved files — only file names change (and only inside the package)
- **Do not migrate `xbrl_exact_splits.py`, `q4_derivation.py`, `concept_fallback_discovery.py`, `fye_month.py`, `quarter_identity.py`, `av_client.py`, or any `get_*` data subagent** — those are separate refactors

---

## 4. Risk Model

### 4.1 Highest-risk area: path math

Current builder files use `Path(__file__).resolve().parents[2]` as repo root. That works from `scripts/earnings/*.py`:

```text
/home/faisal/EventMarketDB/scripts/earnings/build_consensus.py
parents[0] = scripts/earnings
parents[1] = scripts
parents[2] = /home/faisal/EventMarketDB
```

After moving to `scripts/earnings/builders/*.py`, the same expression becomes wrong:

```text
/home/faisal/EventMarketDB/scripts/earnings/builders/consensus.py
parents[0] = scripts/earnings/builders
parents[1] = scripts/earnings
parents[2] = scripts
parents[3] = /home/faisal/EventMarketDB
```

If not fixed, it breaks:

- `.env` loading
- `neograph` imports
- `av_client` imports
- `xbrl_exact_splits` imports
- `fiscal_math` imports
- `sec_quarter_cache_loader` refresh imports
- `pit_fetch.py` subprocess path
- skill-script imports

**Therefore `_paths.py` is mandatory before moving any canonical code.** All `parents[2]` math centralizes to `_paths.REPO_ROOT`, eliminating the risk of a missed site.

### 4.2 Second-highest-risk area: `warmup_cache.py`

`warmup_cache.py` is not just a bundle builder. It is also an extraction warmup CLI with modes:

```text
TICKER                              # concept/member cache
TICKER --transcript TRANSCRIPT_ID
TICKER --mda ACCESSION
TICKER --8k ACCESSION
TICKER --8k-packet ACCESSION
TICKER --guidance-history [--pit ISO8601]
TICKER --inter-quarter --prev-8k ISO8601 --context-cutoff ISO8601
--test
```

It is invoked by extraction skills through:

```bash
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh ...
```

The shell wrapper executes:

```bash
python3 "$SCRIPT_DIR/warmup_cache.py" "$@"
```

So the old `.claude/.../warmup_cache.py` path must remain executable forever. The shim must add repo root to `sys.path` before importing the package, because running from `.claude/.../scripts` does not naturally put repo root first. The shim uses `Path(__file__).resolve().parents[4]` to find repo root from that location.

### 4.3 Third-highest-risk area: private helpers reachable by name

Several modules import private helpers from old files. Old shims must re-export ALL non-dunder names, not only public build functions. The `globals().update()` shim mechanism handles this automatically.

Minimum helper compatibility required:

```text
warmup_cache._parse_dt_for_pit
peer_earnings_snapshot._parse_dt_for_pit
build_prior_financials.classify_period
build_prior_financials.is_target_period
build_prior_financials._parse_value
build_prior_financials.METRIC_REGISTRY
build_prior_financials.dedupe_facts
```

### 4.4 Fourth-highest-risk area: live services

Builder tests may touch:

- Neo4j
- Redis
- Alpha Vantage
- Polygon
- Yahoo Finance
- Benzinga via `pit_fetch.py`

The migration must separate:

- **Fast deterministic gates:** compile, import, identity, static checks, mocked behavior tests
- **Integration gates:** adapter validation, builder validation, selected real compare/render smoke
- **Optional rate-limited gates:** Alpha Vantage live consensus tests (opt-in via `--allow-av`)

**Do not make the PR dependent on today's Alpha Vantage quota** unless the command explicitly opts into `--allow-av`.

### 4.5 Singleton + cross-module shadow risk

- `build_consensus._classifier` — module-level mutable singleton; Stage 7 identity test asserts cross-path consistency
- `_parse_dt_for_pit` exists in BOTH `warmup_cache` and `peer_earnings_snapshot` as DIFFERENT functions; Stage 11 disambiguation test asserts they remain distinct objects after the move

### 4.6 Exact path and import hazards to re-audit during implementation

These are verified current-code facts and must be checked again after copying each module into `scripts/earnings/builders/`:

```text
builder_adapters.py
  - Inserts repo root, scripts/earnings, and skill scripts into sys.path
  - Imports underlying builders lazily inside adapter functions
  - Must stay lazy after migration to preserve startup side-effect timing
  - Has no CLI contract

build_consensus.py
  - Inserts Path(__file__).resolve().parents[2] at import time (line 35)
  - _load_env() reads parents[2] / ".env" (line 71)
  - _get_fye_month() temporarily inserts parents[2] / "scripts" for sec_quarter_cache_loader
  - _build_quarter_ends() and _map_yahoo_periods_to_fdes() temporarily insert
    parents[2] / ".claude/skills/earnings-orchestrator/scripts" for fiscal_math
  - These must use _paths.REPO_ROOT, _paths.ENV_PATH, _paths.SCRIPTS_DIR, or
    _paths.SKILL_SCRIPTS_DIR after relocation
  - Module-level mutable: _classifier (lazy singleton)

build_prior_financials.py
  - Inserts Path(__file__).resolve().parents[2] at import time (line 34)
  - Defines _FM_DIR from parents[2] / ".claude/skills/earnings-orchestrator/scripts" (lines 37-39)
  - _load_env() reads parents[2] / ".env" (line 165)
  - _get_fye_month() temporarily inserts parents[2] / "scripts" for sec_quarter_cache_loader (line 272)
  - Imports get_quarterly_filings, fiscal_math, xbrl_exact_splits, neograph through legacy path behavior
  - Lazy outbound import at line 1593: from xbrl_exact_splits import extract_segment_splits, build_revenue_splits_section
  - These imports must continue to resolve after relocation

macro_snapshot.py
  - Inserts Path(__file__).resolve().parents[2] at import time (line 48)
  - Defines PIT_FETCH from parents[2] / ".claude/skills/earnings-orchestrator/scripts/pit_fetch.py" (line 54)
  - _load_polygon_key() reads parents[2] / ".env" (line 59)
  - Uses neograph, subprocess PIT fetch, Polygon, Yahoo, timezone logic
  - PIT_FETCH and .env must move to _paths.skill_script("pit_fetch.py") and _paths.ENV_PATH

peer_earnings_snapshot.py
  - Inserts Path(__file__).resolve().parents[2] for neograph import (line 25)
  - Uses tempfile, Neo4j query results, PIT return nulling, render_text
  - Internal helper _parse_dt_for_pit imported externally by tests

.claude/skills/earnings-orchestrator/scripts/warmup_cache.py
  - Hard-codes /home/faisal/EventMarketDB skill-script path (line 36)
  - Hard-codes /home/faisal/EventMarketDB repo root (line 37)
  - These are absolute paths (NOT __file__-based) — survive the move logically but
    we still replace with _paths.ensure_legacy_paths() for consistency
  - Imports guidance_ids from skill scripts (line 135, lazy)
  - Imports utils.market_session later (line 1509, lazy)
  - Every CLI mode and /tmp output path must survive unchanged
```

The implementation is not complete until `rg` confirms no moved canonical builder module still contains stale `parents[2]` repo-root assumptions or the hard-coded `/home/faisal/EventMarketDB` path (Section 6 covers this).

---

## 5. Compatibility Shim Requirements

Old Python files in scope become shims using one of three structures.

### 5.1 Shim template — old CLI-capable files under `scripts/earnings/`

For `build_consensus.py`, `build_prior_financials.py`, `macro_snapshot.py`, `peer_earnings_snapshot.py`:

```python
#!/usr/bin/env python3
"""Compatibility shim. Canonical implementation lives in scripts.earnings.builders.<module>.

This file exists ONLY to satisfy bare-name imports
    from <module> import X
that work because callers do `sys.path.insert(0, scripts/earnings)`.

DO NOT add logic here. All behavior lives in the canonical module.

Identity contract: every symbol re-exported by this shim MUST be the SAME
object (Python `is`) as the canonical-module symbol. The two-step mechanism
below guarantees this for ALL non-dunder names (public + private):

1. `for _name in dir(_impl): if not _name.startswith("__"): globals()[_name] = getattr(_impl, _name)`
   — binds every non-dunder name to the shim's module globals. This makes
   `from <shim> import _priv_helper` resolve correctly with byte-identical
   identity to the canonical module's `_priv_helper`.

2. `__all__ = [_name for _name in dir(_impl) if not _name.startswith("_")]`
   — public names only. Preserves the original module's `from <shim> import *`
   semantics: original modules had no `__all__`, so `*`-import defaulted to
   public-only; shim must match.

The combination is critical. Using the simpler `__all__ = [n for n in dir(_impl)
if not n.startswith("__")]` (i.e. excluding only dunders) would leak private
helpers through `*`-imports — a silent behavior change. The static AST test
in test_builders_static.py asserts `__all__` excludes underscore names.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.earnings.builders import <module> as _impl

# Bind ALL non-dunder names (public + private) so direct imports work,
# but expose only PUBLIC names through `__all__` to preserve `from X import *`
# semantics that the original module had.
for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)
__all__ = [_name for _name in dir(_impl) if not _name.startswith("_")]
del _name

if __name__ == "__main__":
    _impl.main()
```

### 5.2 Shim template — old module-only `scripts/earnings/builder_adapters.py`

```python
#!/usr/bin/env python3
"""Compatibility shim. Canonical implementation lives in scripts.earnings.builders.adapters."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.earnings.builders import adapters as _impl

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)
__all__ = [_name for _name in dir(_impl) if not _name.startswith("_")]
del _name

# No __main__ block — builder_adapters.py has no main()
```

### 5.3 Shim template — `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py`

**CRITICAL**: warmup_cache.py is the ONLY file in scope whose old `__main__`
block dispatches BEFORE calling `main()`. Specifically (verified at the OLD
file's line 2063):

```python
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        sys.exit(0 if _run_v2_regression_tests() else 1)
    main()
```

`--test` is handled in the bottom block, NOT inside `main()`. A naive
`_impl.main()` shim would silently break `python warmup_cache.py --test` and
`bash warmup_cache.sh --test`. The shim must REPLICATE the old dispatch:

```python
#!/usr/bin/env python3
"""Compatibility shim. Canonical implementation lives in scripts.earnings.builders.warmup_cache.

This file ALSO serves as the script target for warmup_cache.sh — the shell
wrapper does `exec python3 "$SCRIPT_DIR/warmup_cache.py" "$@"`, so removing
this file would break agent calls. The shim's __main__ block REPLICATES the
canonical module's pre-main() dispatch (--test → _run_v2_regression_tests),
which is NOT inside main() itself.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]   # .claude/skills/earnings-orchestrator/scripts → repo
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.earnings.builders import warmup_cache as _impl

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)
__all__ = [_name for _name in dir(_impl) if not _name.startswith("_")]
del _name

if __name__ == "__main__":
    # Mirror the OLD __main__ dispatch exactly. _run_v2_regression_tests()
    # returns a bool (verified: `return failed == 0`), so sys.exit() with
    # the inverted truth value preserves the old exit-code semantic.
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        sys.exit(0 if _impl._run_v2_regression_tests() else 1)
    _impl.main()
```

The 4 other CLI-capable builders (`build_consensus.py`, `build_prior_financials.py`, `macro_snapshot.py`, `peer_earnings_snapshot.py`) all do `if __name__ == "__main__": main()` directly with no pre-dispatch, so the §5.1 template's plain `_impl.main()` is correct for them. **Only warmup_cache needs this special case.**

### Why this shim shape

- Preserves old imports.
- Preserves CLI execution.
- Re-exports private helpers automatically (no enumeration risk).
- Gives identical function objects for old and new import paths.
- Keeps real logic in exactly one canonical module.
- Survives `rg "def build_"` static check (shim has zero `def`/`class` nodes).
- **`from <shim> import *` semantics match the original module** because `__all__` excludes underscore names — preserving the same wildcard-import surface the canonical module had.

**Do not use simple star imports for these shims.** Star import excludes underscore names unless module defines `__all__`, and the canonical modules do not.

---

## 6. New `_paths.py` Contract

Add `scripts/earnings/builders/_paths.py` BEFORE moving any implementation. This is the load-bearing centralization.

### Required content

```python
"""Centralized repo-root + sys.path discipline for the builders subpackage.

Every canonical builder module imports from this helper. Old files using
Path(__file__).resolve().parents[2] historically assumed the file lived at
scripts/earnings/<X>.py; the same expression breaks at scripts/earnings/builders/<X>.py.
This module eliminates that risk by computing paths from THIS file's location
(parents[3] from scripts/earnings/builders/_paths.py = repo root).
"""
from __future__ import annotations

import sys
from pathlib import Path

# parents[0] = builders, parents[1] = earnings, parents[2] = scripts, parents[3] = repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
EARNINGS_DIR = REPO_ROOT / "scripts" / "earnings"
SKILL_SCRIPTS_DIR = REPO_ROOT / ".claude" / "skills" / "earnings-orchestrator" / "scripts"
ENV_PATH = REPO_ROOT / ".env"


def ensure_legacy_paths() -> None:
    """Insert the four directories that builders historically relied on, in
    the EXACT precedence order builder_adapters.py used.

    Current builder_adapters.py inserts repo root, then scripts/earnings, then
    .claude/.../scripts each at index 0, leaving effective precedence:
      skill-scripts > earnings-local > scripts/ > repo root.

    This function reproduces that precedence exactly while being idempotent
    (calling it twice does not duplicate entries) and deterministic under
    pytest, direct CLI execution, python -m, and old sys.path-mutating scripts.
    """
    desired = (SKILL_SCRIPTS_DIR, EARNINGS_DIR, SCRIPTS_DIR, REPO_ROOT)
    for path in desired:
        s = str(path)
        while s in sys.path:
            sys.path.remove(s)
    for path in reversed(desired):
        sys.path.insert(0, str(path))


def skill_script(name: str) -> str:
    """Resolve a path to a script file inside the earnings-orchestrator skill."""
    return str(SKILL_SCRIPTS_DIR / name)
```

### Usage in canonical builder modules

Every canonical builder module in `scripts/earnings/builders/` must call `ensure_legacy_paths()` near the top before bare legacy imports. Example for `consensus.py`:

```python
from __future__ import annotations
import json, logging, os, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from ._paths import ensure_legacy_paths, ENV_PATH
ensure_legacy_paths()

from av_client import fetch_av_json, make_false_empty_checker  # bare import works after ensure_legacy_paths
```

### Why path order matters

Current `builder_adapters.py` inserts repo root, then `scripts/earnings`, then the skill scripts directory, each at index `0`, leaving skill scripts first in effective precedence. The new helper preserves this exactly. **Do not change this order without a separate import-shadowing audit.**

The remove-then-reinsert behavior is intentional — it makes path precedence deterministic under pytest, direct CLI execution, `python -m`, and old sys.path-mutating scripts, while avoiding duplicate path entries.

### Static guard after each canonical copy

Run after Stages 2, 4, 6, 8, 10, 12 (every COPY stage):

```bash
! rg -n "parents\[2\]|/home/faisal/EventMarketDB" scripts/earnings/builders/<just-moved>.py
```

Expected:
- No stale `parents[2]` repo-root math
- No hard-coded `/home/faisal/EventMarketDB`
- Any remaining `Path(__file__)` usage must be local-file safe and explicitly reviewed

---

## 7. Canonical Package Public API

`scripts/earnings/builders/__init__.py` should re-export ONLY the seven adapter entrypoints used by the orchestrator:

```python
"""scripts.earnings.builders — canonical builder package.

Public surface: the 7 adapter functions used by earnings_orchestrator.py.
Underlying builders are reachable via their submodules
(e.g. scripts.earnings.builders.consensus.build_consensus).

Import discipline:
  - Bare imports (e.g. `from build_consensus import X`) keep working via 1-line
    shim files at the OLD paths. Tests assert this with the 4-path identity
    invariant in test_builders_imports.py.
  - Qualified imports (`from scripts.earnings.builders.consensus import X`)
    work after the corresponding move-stage lands.
  - Do NOT delete any shim file at an OLD path. They are permanent.
"""
from __future__ import annotations

from .adapters import (
    build_8k_packet,
    build_guidance_history,
    build_inter_quarter_context,
    build_peer_earnings_snapshot,
    build_macro_snapshot,
    build_consensus,
    build_prior_financials,
)

__all__ = [
    "build_8k_packet",
    "build_guidance_history",
    "build_inter_quarter_context",
    "build_peer_earnings_snapshot",
    "build_macro_snapshot",
    "build_consensus",
    "build_prior_financials",
]
```

**Do not re-export every helper from package root.** Helpers remain importable from their submodules.

---

## 8. ⚠ Tool-call hygiene — MUST READ before any stage

**Claude Code spawns a fresh shell per `Bash` tool call.** Shell state — `cd`, `export VAR=...`, `pushd` — does NOT persist across calls.

- The pre-flight block does `cd "$WORKTREE"` and `export REPO=...`, but **those die at the end of that one Bash call**. Subsequent Bash calls start back at `/home/faisal/EventMarketDB` (the MAIN repo, NOT the worktree).
- Forgetting this means accidentally editing/testing/committing on `main` instead of the worktree — production sees stages 0–14 — defeating the entire worktree isolation.

**Discipline (mandatory for every tool call from §10 onward):**

1. **Bash:** every command starts with `cd /home/faisal/em-builders-restructure && ...`, OR every multi-line Bash block opens with `cd /home/faisal/em-builders-restructure` as its first effective command. Use the literal path; don't rely on `$WORKTREE` carrying over.
2. **Edit / Write:** every `file_path` parameter uses the absolute worktree path:
   - ✓ `/home/faisal/em-builders-restructure/scripts/earnings/builders/consensus.py`
   - ✗ `scripts/earnings/builders/consensus.py` (repo-relative — Edit interprets relative to its own cwd)
   - ✗ `/home/faisal/EventMarketDB/scripts/earnings/builders/consensus.py` (this is MAIN — defeats worktree isolation)
3. **Python executable:** the venv lives in main (`/home/faisal/EventMarketDB/venv/bin/python`). That absolute path stays the same regardless of which checkout you're operating on — only source code is in the worktree.
   **STRICT RULE:** every Bash code block in this plan that uses `$PY` must EITHER define `PY=/home/faisal/EventMarketDB/venv/bin/python` as its FIRST or SECOND effective line, OR use the absolute path inline. Shell state does not persist across tool calls; a `$PY` reference without a same-block definition expands to empty and silently runs against the system shell. The canonical opening for every gate block in this plan is:
   ```bash
   cd /home/faisal/em-builders-restructure
   PY=/home/faisal/EventMarketDB/venv/bin/python
   ```
   When in doubt, prepend that pair. The plan's per-stage gate template (§10) does this; if you're cherry-picking a sub-block, copy both lines.
4. **`PYTHONPATH=scripts/earnings`** is the project's canonical PYTHONPATH discipline. Every test gate sets it; do not omit.

**Safety check after every stage** (before committing): scope the check to the
EXACT 11 migration target files. The main checkout may already have unrelated
dirt (test stubs, stale skill .md files); a broad glob like `.claude/skills/`
would false-fail. Use this fenced glob:

```bash
cd /home/faisal/EventMarketDB && git status -s -- \
    scripts/earnings/build_consensus.py \
    scripts/earnings/build_prior_financials.py \
    scripts/earnings/macro_snapshot.py \
    scripts/earnings/peer_earnings_snapshot.py \
    scripts/earnings/builder_adapters.py \
    scripts/earnings/earnings_orchestrator.py \
    scripts/earnings/render_section.py \
    scripts/earnings/compare_section.py \
    scripts/earnings/concept_fallback_discovery.py \
    scripts/earnings/q4_derivation.py \
    .claude/skills/earnings-orchestrator/scripts/warmup_cache.py
# expect: NO output during stages 0–15 (main is unchanged for these 11 files;
#         dirt in OTHER files of main is the user's pre-existing state, ignore).
```

If this command shows ANY changes among the 11 files during stages 0–15,
you've accidentally edited the main checkout. **DO NOT auto-revert.** STOP and
ask the user: those changes might be the user's own in-progress work that
collided with your accidental edit. Manually inspect each modified file with
`git diff -- <file>` and let the user decide whether to keep, stash, or
discard. Then re-run the stage in the worktree using the absolute path.

---

## 9. Pre-flight Procedure

### §9.1 Environment + main-checkout sanity

```bash
set -eo pipefail
MAIN_REPO=/home/faisal/EventMarketDB
PY=/home/faisal/EventMarketDB/venv/bin/python
cd "$MAIN_REPO"

# §9.1.1 — main is on the expected commit (post-renderer-move)
git branch --show-current   # expect: main
git log --oneline -3        # expect: 6bb2c6d (4-path identity test) at top

# §9.1.2 — confirm the 6 source files are at their expected locations
test -f scripts/earnings/build_consensus.py
test -f scripts/earnings/build_prior_financials.py
test -f scripts/earnings/macro_snapshot.py
test -f scripts/earnings/peer_earnings_snapshot.py
test -f scripts/earnings/builder_adapters.py
test -f .claude/skills/earnings-orchestrator/scripts/warmup_cache.py
test -f .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh
echo "all 6 source files + .sh wrapper present"

# §9.1.3 — confirm scripts.earnings is a namespace package today
PYTHONPATH=. $PY -c "
import scripts.earnings
assert type(scripts.earnings).__name__ == 'module'
print('scripts.earnings is reachable, __path__ =', scripts.earnings.__path__)
"

# §9.1.4 — venv has required deps
$PY -c "import dotenv, neo4j, pandas; print('venv deps OK')"

# §9.1.5 — baseline: existing renderer + orchestrator gates green
PYTHONPATH=scripts/earnings $PY -m pytest \
    scripts/earnings/test_renderer_*.py \
    scripts/earnings/test_orchestrator_pit_mode.py \
    --ignore=scripts/earnings/test_fmt_guards.py \
    -q
# expect: 167+ passed (renderer baseline)

# §9.1.6 — orchestrator inline self-test (load-bearing)
PYTHONPATH=scripts/earnings $PY scripts/earnings/earnings_orchestrator.py --test
# expect: "9 passed, 0 failed out of 9"

# §9.1.7 — warmup_cache.sh --test works
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh --test
# expect: regression-test output, no crashes
```

### §9.2 Worktree creation

```bash
WORKTREE=/home/faisal/em-builders-restructure
if [ -d "$WORKTREE" ]; then
  echo "FATAL: worktree $WORKTREE already exists."
  echo "  cd $MAIN_REPO && git worktree remove --force $WORKTREE"
  exit 1
fi
if git show-ref --verify --quiet refs/heads/builders-restructure; then
  echo "FATAL: branch builders-restructure already exists."
  echo "  cd $MAIN_REPO && git branch -D builders-restructure"
  exit 1
fi

# Confirm target files clean on main
TARGETS=(
  "scripts/earnings/build_consensus.py"
  "scripts/earnings/build_prior_financials.py"
  "scripts/earnings/macro_snapshot.py"
  "scripts/earnings/peer_earnings_snapshot.py"
  "scripts/earnings/builder_adapters.py"
  "scripts/earnings/earnings_orchestrator.py"
  "scripts/earnings/render_section.py"
  "scripts/earnings/compare_section.py"
  "scripts/earnings/concept_fallback_discovery.py"
  "scripts/earnings/q4_derivation.py"
  ".claude/skills/earnings-orchestrator/scripts/warmup_cache.py"
  ".claude/skills/earnings-orchestrator/scripts/warmup_cache.sh"
)
for f in "${TARGETS[@]}"; do
  git diff --quiet HEAD -- "$f" || { echo "DIRTY: $f"; exit 1; }
  git diff --cached --quiet HEAD -- "$f" || { echo "STAGED-DIRTY: $f"; exit 1; }
done
echo "all 12 target files clean on main"

# Create worktree
git worktree add "$WORKTREE" -b builders-restructure main
cd "$WORKTREE"
echo "worktree at $(pwd) on branch $(git branch --show-current)"

# §9.2.1 — Symlink .env from main into worktree (gitignored, not carried over)
# `git worktree add` only checks out tracked files. The .env file (with
# ALPHAVANTAGE_API_KEY, POLYGON_API_KEY, NEO4J_PASSWORD, etc.) is gitignored,
# so the worktree won't have it. Builders that call _load_env() need it.
if [ ! -e "$WORKTREE/.env" ] && [ -f "$MAIN_REPO/.env" ]; then
  ln -s "$MAIN_REPO/.env" "$WORKTREE/.env"
  echo "Symlinked .env from main repo (live tests will need it)"
elif [ -e "$WORKTREE/.env" ]; then
  echo ".env already present in worktree"
else
  echo "WARNING: $MAIN_REPO/.env does not exist — live integration tests will fail"
fi
```

### §9.3 Integration validation (MANDATORY before merge — see §12 final gate)

```bash
# Run if Neo4j reachable — these establish a behavioral baseline before any changes
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
$PY scripts/earnings/test_adapter_validation.py --ticker FIVE
$PY scripts/earnings/test_builder_validation.py --ticker FIVE
```

Alpha Vantage gate is opt-in (quota can be exhausted externally); if rate-limited, do not block the package relocation on it. The two validation scripts above ARE mandatory at the final gate (§12).

---

## 10. Staged Implementation Plan

Each stage is a separate commit. After each stage, run that stage's gate. If any stage fails, fix before continuing. **Do not batch stages.**

### Stage 0 — TDD foundation (4 commits, no canonical-code moves)

#### Goal
Capture every observable behavior of the 6 modules so any divergence introduced by a later stage is detected BEFORE commit.

#### Commit 0.1 — Baseline tag + packet snapshots

```bash
cd /home/faisal/em-builders-restructure

# CRITICAL: tag CURRENT HEAD before any builders commits, so the tag points
# to the pre-Stage-0 state. This makes `git revert tag..HEAD` reliably revert
# ALL stage-0 commits (otherwise the tag would point to commit 0.1 itself,
# leaving the empty commit un-reverted).
PY=/home/faisal/EventMarketDB/venv/bin/python
git tag pre-builders-restructure-baseline HEAD

git commit --allow-empty -m "chore(builders): tag pre-builders-restructure baseline (commit 0.1/20)"

# Capture old-path packets for stable historical cases (used by Stage 8.4 normalized comparisons)
mkdir -p /tmp/builders_baseline
$PY scripts/earnings/build_prior_financials.py CHRW \
  --pit 2025-04-01T00:00:00+00:00 \
  --period-of-report 2024-12-31 \
  --out-path /tmp/builders_baseline/prior_financials_chrw.json

$PY scripts/earnings/peer_earnings_snapshot.py AVGO \
  --pit 2023-12-07T16:18:51-05:00 \
  --out-path /tmp/builders_baseline/peer_earnings_avgo.json

$PY scripts/earnings/macro_snapshot.py AVGO \
  --pit 2023-12-07T16:18:51-05:00 \
  --session post_market \
  --source yahoo \
  --out-path /tmp/builders_baseline/macro_avgo.json

ls -la /tmp/builders_baseline/
```

#### Commit 0.2 — Public-surface inventory test

**Add file** `/home/faisal/em-builders-restructure/scripts/earnings/test_builders_surface.py`:

```python
"""Surface inventory — every public name + private cross-export must be reachable.

This test is the SHIM CONTRACT — it codifies which symbols MUST survive the move.
Stages 2-13 each add bindings (via shim re-exports); none of them can ever
REMOVE a symbol from any path listed here.
"""
from __future__ import annotations
import importlib
import sys
from pathlib import Path
import pytest

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
sys.path.insert(0, str(THIS_DIR.parent.parent / ".claude/skills/earnings-orchestrator/scripts"))


# Module name -> {public: [...], private_exports: [...]}
EXPECTED_SURFACE: dict[str, dict[str, list[str]]] = {
    "build_consensus": {
        "public": ["build_consensus", "main"],
        "private_exports": ["_parse_iso", "_normalize_session"],
    },
    "build_prior_financials": {
        "public": ["build_prior_financials", "classify_period", "is_target_period",
                   "dedupe_facts", "main"],
        "private_exports": ["_parse_value"],
    },
    "macro_snapshot": {
        "public": ["build_macro_snapshot", "render_text", "main"],
        "private_exports": [],
    },
    "peer_earnings_snapshot": {
        "public": ["build_peer_earnings_snapshot", "render_text", "main"],
        "private_exports": ["_parse_dt_for_pit"],
    },
    "warmup_cache": {
        "public": ["build_8k_packet", "build_guidance_history",
                   "build_inter_quarter_context", "render_guidance_text",
                   "render_inter_quarter_text", "run_warmup", "run_transcript",
                   "run_mda", "run_8k", "main"],
        "private_exports": ["_parse_dt_for_pit", "_run_v2_regression_tests"],
    },
    "builder_adapters": {
        "public": ["build_8k_packet", "build_guidance_history",
                   "build_inter_quarter_context", "build_peer_earnings_snapshot",
                   "build_macro_snapshot", "build_consensus", "build_prior_financials"],
        "private_exports": [],
    },
}


@pytest.mark.parametrize("modname,spec", EXPECTED_SURFACE.items())
def test_module_exposes_expected_surface(modname, spec):
    mod = importlib.import_module(modname)
    for sym in spec["public"] + spec["private_exports"]:
        assert hasattr(mod, sym), f"{modname} missing required symbol {sym}"


@pytest.mark.parametrize("modname,spec", EXPECTED_SURFACE.items())
def test_no_unexpected_public_names_lost(modname, spec):
    mod = importlib.import_module(modname)
    for sym in spec["public"]:
        obj = getattr(mod, sym)
        assert obj is not None, f"{modname}.{sym} is None — shim missing real binding?"
```

```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_surface.py -v
# expect: 12 passed
git add scripts/earnings/test_builders_surface.py
git commit -m "test(builders): pin public surface contract for 6 builder modules (commit 0.2/20)"
```

#### Commit 0.3 — CLI smoke harness + pytest marker registration

**REGISTER MARKERS FIRST.** This commit introduces `@pytest.mark.live` and
`@pytest.mark.builders`. Pytest emits `PytestUnknownMarkWarning` for any mark
not declared in `pytest.ini` (or `pyproject.toml`/`setup.cfg`) — and worse,
some CI configurations promote that warning to an error. Register the markers
before the tests reference them.

**Step 1 — extend or create `pytest.ini` at repo root.** First check whether
`pytest.ini` exists:

```bash
cd /home/faisal/em-builders-restructure
ls pytest.ini 2>/dev/null && echo "exists — append" || echo "missing — create"
```

If it exists, append a `markers =` block (or extend the existing one). If it
doesn't, create one with this content:

```ini
[pytest]
markers =
    live: tests that hit Neo4j / Alpha Vantage / Polygon / Yahoo / Benzinga (excluded from default gates; enable with `-m live`)
    builders: tests added by the builders-restructure migration (file-wide grouping; not used for selection)
```

If `pytest.ini` already had a `[pytest]` section with `markers =`, the two
new lines must be added under that key (pytest expects the indented continuation
syntax for multi-value keys).

**Step 2 — verify registration:**

```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
PYTHONPATH=scripts/earnings $PY -m pytest --markers 2>&1 | grep -E "@pytest\.mark\.(live|builders)"
# expect: BOTH markers listed
```

If either marker is missing from `--markers` output, fix `pytest.ini` before
proceeding.

**Step 3 — add the CLI smoke file.** Add file `/home/faisal/em-builders-restructure/scripts/earnings/test_builders_cli_smoke.py`:

```python
"""CLI smoke — every builder __main__ block must run without crashing.

Markers:
  - @pytest.mark.builders: groups all builders-restructure tests (file-wide)
  - @pytest.mark.live:     test hits Neo4j / Polygon / Yahoo / AV. EXCLUDED from
                           per-stage gates by default. Enable with `-m live`.

The two --test rows below are NOT marked live (they run no external service).
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[2]
# CRITICAL: use the running interpreter — `git worktree add` does NOT carry
# gitignored venv/, so REPO/venv/bin/python may not exist in the worktree.
PY = sys.executable
PIT_TS = "2024-09-15T16:00:00+00:00"
TICKER = "FIVE"

pytestmark = pytest.mark.builders   # file-wide marker for grouping


def _run(argv, timeout=90):
    # CRITICAL: dict-merge order matters — explicit values must come AFTER
    # **os.environ so they override any inherited PYTHONPATH. The reverse
    # order ({"PYTHONPATH": ..., **os.environ}) lets the caller's PYTHONPATH
    # silently override the test's intended value.
    return subprocess.run(
        argv, check=True, timeout=timeout, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(REPO / "scripts/earnings")},
    )


# Fast --test rows (no DB; load-bearing — run in every per-stage gate)
def test_cli_warmup_cache_test_flag():
    _run([PY, str(REPO / ".claude/skills/earnings-orchestrator/scripts/warmup_cache.py"), "--test"])


def test_cli_warmup_cache_sh_test_flag():
    _run(["bash", str(REPO / ".claude/skills/earnings-orchestrator/scripts/warmup_cache.sh"), "--test"])


# Live-data rows — explicitly marked so default gates can exclude with `-m "not live"`.
@pytest.mark.live
def test_cli_build_consensus():
    _run([PY, str(REPO / "scripts/earnings/build_consensus.py"), TICKER, "--pit", PIT_TS])


@pytest.mark.live
def test_cli_build_prior_financials():
    _run([PY, str(REPO / "scripts/earnings/build_prior_financials.py"), TICKER, "--pit", PIT_TS])


@pytest.mark.live
def test_cli_macro_snapshot():
    _run([PY, str(REPO / "scripts/earnings/macro_snapshot.py"), TICKER, "--pit", PIT_TS])


@pytest.mark.live
def test_cli_peer_earnings_snapshot():
    _run([PY, str(REPO / "scripts/earnings/peer_earnings_snapshot.py"), TICKER, "--pit", PIT_TS])
```

```bash
# Per-stage default — only the two --test rows (non-live, fast)
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
PYTHONPATH=scripts/earnings $PY -m pytest \
    scripts/earnings/test_builders_cli_smoke.py -v -m "not live"
# expect: 2 passed, 4 deselected

# Live integration (run only in §12 final gate, or manually with --allow-live):
# PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_cli_smoke.py -v -m live
git add scripts/earnings/test_builders_cli_smoke.py pytest.ini
git commit -m "test(builders): CLI smoke harness + register live/builders pytest markers (commit 0.3/20)"
```

#### Commit 0.4 — Identity-test scaffold (active, empty MODULE_PAIRS)

**Add file** `/home/faisal/em-builders-restructure/scripts/earnings/test_builders_imports.py`:

```python
"""4-path identity invariant — load-bearing regression guard.

After each move stage, every relocated symbol must resolve to the SAME Python
object via `is` from EVERY import path:
  1. Old bare path        (e.g. `from build_consensus import build_consensus`)
  2. Old qualified path   (e.g. `from scripts.earnings.build_consensus import build_consensus`)
  3. New qualified path   (e.g. `from scripts.earnings.builders.consensus import build_consensus`)

Stages 3, 5, 7, 9, 11, 13 each extend MODULE_PAIRS with rows for the symbols
their shim-stage relocates. Stage 15 promotes this test to permanent regression
guard with completeness asserts.
"""
from __future__ import annotations
import importlib
import sys
from pathlib import Path
import pytest

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent.parent

# Deterministic sys.path discipline — mirrors _paths.ensure_legacy_paths().
# remove-then-reinsert pattern guarantees the precedence order is:
#   skill-scripts > earnings-local > repo root
# even if any of these were ALREADY on sys.path at a different index.
LEGACY_PATHS = (
    # MUST mirror _paths.ensure_legacy_paths() exactly: 4 entries in this order.
    # Missing PROJECT_ROOT / "scripts" would cause `from sec_quarter_cache_loader
    # import refresh_ticker` (lives at scripts/sec_quarter_cache_loader.py) to
    # ImportError during identity tests of build_consensus / build_prior_financials.
    PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts",
    PROJECT_ROOT / "scripts/earnings",
    PROJECT_ROOT / "scripts",
    PROJECT_ROOT,
)
for path in LEGACY_PATHS:
    s = str(path)
    while s in sys.path:
        sys.path.remove(s)
for path in reversed(LEGACY_PATHS):
    sys.path.insert(0, str(path))


# {old_module_bare: (new_module_qualified, [symbols])}
# Populated incrementally by Stages 3, 5, 7, 9, 11, 13.
MODULE_PAIRS: dict[str, tuple[str, list[str]]] = {}


def _flatten_pairs():
    """Flatten MODULE_PAIRS into parametrize-friendly tuples."""
    rows = []
    for old_bare, (new_qual, symbols) in MODULE_PAIRS.items():
        for sym in symbols:
            rows.append((old_bare, new_qual, sym))
    return rows


@pytest.mark.parametrize("old_bare,new_qual,symbol", _flatten_pairs())
def test_old_bare_equals_new_qualified(old_bare, new_qual, symbol):
    """Bare-name import (relies on PYTHONPATH=scripts/earnings) must resolve
    to the same object as the canonical qualified path."""
    bare_mod = importlib.import_module(old_bare)
    new_mod = importlib.import_module(new_qual)
    assert getattr(bare_mod, symbol) is getattr(new_mod, symbol), (
        f"IDENTITY BROKEN: {old_bare}.{symbol} ({id(getattr(bare_mod, symbol))}) "
        f"is not {new_qual}.{symbol} ({id(getattr(new_mod, symbol))})"
    )


@pytest.mark.parametrize("old_bare,new_qual,symbol", _flatten_pairs())
def test_old_qualified_equals_new_qualified(old_bare, new_qual, symbol):
    """Old qualified path (e.g. scripts.earnings.build_consensus) must resolve
    to the same object as the canonical qualified path."""
    if old_bare == "warmup_cache":
        # warmup_cache lives outside scripts.earnings.* — no qualified old path
        pytest.skip("warmup_cache has no scripts.earnings.* qualified old path")
    old_qual = f"scripts.earnings.{old_bare}"
    old_mod = importlib.import_module(old_qual)
    new_mod = importlib.import_module(new_qual)
    assert getattr(old_mod, symbol) is getattr(new_mod, symbol), (
        f"IDENTITY BROKEN: {old_qual}.{symbol} is not {new_qual}.{symbol}"
    )
```

```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_imports.py -v
# expect: 0 tests collected (parametrize over empty list = no rows; passes trivially)
git add scripts/earnings/test_builders_imports.py
git commit -m "test(builders): identity-test scaffold (commit 0.4/20)"
```

#### Stage 0 final gate

```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
# Default: exclude live tests; only the two warmup_cache --test rows run from CLI smoke
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_*.py -v -m "not live"
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_renderer_*.py -q
PYTHONPATH=scripts/earnings $PY scripts/earnings/earnings_orchestrator.py --test
# Safety check: main is untouched
cd /home/faisal/EventMarketDB && git status -s -- scripts/earnings/build_consensus.py scripts/earnings/build_prior_financials.py scripts/earnings/macro_snapshot.py scripts/earnings/peer_earnings_snapshot.py scripts/earnings/builder_adapters.py scripts/earnings/earnings_orchestrator.py scripts/earnings/render_section.py scripts/earnings/compare_section.py scripts/earnings/concept_fallback_discovery.py scripts/earnings/q4_derivation.py .claude/skills/earnings-orchestrator/scripts/warmup_cache.py
# expect: empty
```

#### Stage 0 rollback
```bash
# Tag-based revert covers ALL 4 stage-0 commits (works because the tag was
# placed at HEAD BEFORE commit 0.1, see Stage 0.1 above).
cd /home/faisal/em-builders-restructure
git revert --no-edit pre-builders-restructure-baseline..HEAD
git tag -d pre-builders-restructure-baseline
```

---

### Stage 1 — Add `_paths.py` helper module + tests (1 commit)

#### Files changed

```text
scripts/earnings/builders/__init__.py       # empty package surface
scripts/earnings/builders/_paths.py         # the load-bearing centralization
scripts/earnings/test_builders_paths.py     # validates _paths.py
```

#### Edit A — `scripts/earnings/builders/__init__.py`

```python
"""scripts.earnings.builders — relocated builder modules.

Public surface: empty until Stage 12 (when adapters.py is canonicalized).
Underlying builders are reachable via their submodules after Stages 2-11.
"""
from __future__ import annotations

__all__: list[str] = []
```

#### Edit B — `scripts/earnings/builders/_paths.py`

Use the EXACT content from §6.

#### Edit C — `scripts/earnings/test_builders_paths.py`

```python
"""Tests for the centralized path helper. These run BEFORE any canonical-code
move because `_paths.ensure_legacy_paths()` is the load-bearing primitive
that every relocated module relies on.
"""
from __future__ import annotations
import sys
import os
from pathlib import Path
import pytest

from scripts.earnings.builders import _paths


def test_repo_root_resolves_to_actual_repo():
    expected = Path(__file__).resolve().parents[2]
    assert _paths.REPO_ROOT == expected
    assert _paths.REPO_ROOT.exists()


def test_earnings_dir_exists():
    assert _paths.EARNINGS_DIR.exists()
    assert _paths.EARNINGS_DIR.name == "earnings"


def test_skill_scripts_dir_exists():
    assert _paths.SKILL_SCRIPTS_DIR.exists()
    assert (_paths.SKILL_SCRIPTS_DIR / "warmup_cache.py").exists()


def test_scripts_dir_exists():
    assert _paths.SCRIPTS_DIR.exists()
    assert _paths.SCRIPTS_DIR.name == "scripts"


def test_skill_script_resolves_pit_fetch():
    pit = _paths.skill_script("pit_fetch.py")
    assert os.path.exists(pit)
    assert pit.endswith(".claude/skills/earnings-orchestrator/scripts/pit_fetch.py")


def test_env_path_points_to_repo_env():
    # Doesn't assert .env exists (it may not in CI) — only that path is correct
    assert _paths.ENV_PATH == _paths.REPO_ROOT / ".env"


def test_ensure_legacy_paths_inserts_all_four():
    # Save and clear sys.path entries we care about
    saved = list(sys.path)
    expected = (_paths.SKILL_SCRIPTS_DIR, _paths.EARNINGS_DIR,
                _paths.SCRIPTS_DIR, _paths.REPO_ROOT)
    for p in expected:
        s = str(p)
        while s in sys.path:
            sys.path.remove(s)

    try:
        _paths.ensure_legacy_paths()
        for p in expected:
            assert str(p) in sys.path, f"{p} not in sys.path after ensure_legacy_paths"
    finally:
        sys.path[:] = saved


def test_ensure_legacy_paths_is_idempotent():
    saved = list(sys.path)
    try:
        _paths.ensure_legacy_paths()
        first = list(sys.path)
        _paths.ensure_legacy_paths()
        second = list(sys.path)
        assert first == second, "ensure_legacy_paths is not idempotent"
    finally:
        sys.path[:] = saved


def test_ensure_legacy_paths_removes_duplicates():
    saved = list(sys.path)
    try:
        # Insert duplicates
        for p in (_paths.SKILL_SCRIPTS_DIR, _paths.EARNINGS_DIR,
                  _paths.SCRIPTS_DIR, _paths.REPO_ROOT):
            sys.path.insert(0, str(p))
            sys.path.insert(0, str(p))   # duplicate
        _paths.ensure_legacy_paths()
        for p in (_paths.SKILL_SCRIPTS_DIR, _paths.EARNINGS_DIR,
                  _paths.SCRIPTS_DIR, _paths.REPO_ROOT):
            assert sys.path.count(str(p)) == 1, f"{p} appears > 1 time"
    finally:
        sys.path[:] = saved


def test_ensure_legacy_paths_precedence_order():
    """SKILL_SCRIPTS_DIR > EARNINGS_DIR > SCRIPTS_DIR > REPO_ROOT (highest precedence first)."""
    saved = list(sys.path)
    try:
        _paths.ensure_legacy_paths()
        # Find indices
        idx_skill = sys.path.index(str(_paths.SKILL_SCRIPTS_DIR))
        idx_earn = sys.path.index(str(_paths.EARNINGS_DIR))
        idx_scripts = sys.path.index(str(_paths.SCRIPTS_DIR))
        idx_repo = sys.path.index(str(_paths.REPO_ROOT))
        assert idx_skill < idx_earn < idx_scripts < idx_repo
    finally:
        sys.path[:] = saved


def test_lazy_transitive_imports_resolve():
    """Smoke-test that every lazy/transitive import inside builders RESOLVES
    after ensure_legacy_paths() runs.

    These imports fire only when builder functions are CALLED (not at module
    import time), so they would otherwise pass the test suite while silently
    breaking the real code path. Forcing them at the path-helper layer means
    Stage 1 fails fast if ensure_legacy_paths() is wrong.

    Catalog (verified by reconnaissance):
      - fiscal_math                       (consensus, prior_financials)
      - sec_quarter_cache_loader          (consensus, prior_financials)
      - xbrl_exact_splits                 (prior_financials lazy at line 1593)
      - guidance_ids                      (warmup_cache lazy at line 135)
      - utils.market_session              (consensus, warmup_cache)
      - neograph.Neo4jConnection          (all builders that touch Neo4j)
      - av_client                         (consensus top-level bare import)
      - pit_time                          (skill-scripts dir, used by pit_fetch)
    """
    saved = list(sys.path)
    try:
        _paths.ensure_legacy_paths()
        # Each import below MUST succeed. If any fails, ensure_legacy_paths()
        # is missing a path or precedence is wrong.
        import fiscal_math  # noqa: F401
        import sec_quarter_cache_loader  # noqa: F401
        import xbrl_exact_splits  # noqa: F401
        import guidance_ids  # noqa: F401
        from utils.market_session import MarketSessionClassifier  # noqa: F401
        from neograph.Neo4jConnection import get_manager  # noqa: F401
        import av_client  # noqa: F401
        import pit_time  # noqa: F401
    finally:
        sys.path[:] = saved
```

#### Stage 1 verification gate

```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
$PY -m py_compile scripts/earnings/builders/_paths.py scripts/earnings/builders/__init__.py
PYTHONPATH=. $PY -m pytest scripts/earnings/test_builders_paths.py -v
# expect: 10 passed (9 path tests + 1 lazy-imports smoke)
PYTHONPATH=. $PY -c "
import scripts.earnings.builders as b
print('package OK, surface =', b.__all__)
"
# All Stage 0 tests still green (exclude live rows by default)
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_*.py -v -m "not live"
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_renderer_*.py -q
PYTHONPATH=scripts/earnings $PY scripts/earnings/earnings_orchestrator.py --test

# Safety check
cd /home/faisal/EventMarketDB && git status -s -- scripts/earnings/build_consensus.py scripts/earnings/build_prior_financials.py scripts/earnings/macro_snapshot.py scripts/earnings/peer_earnings_snapshot.py scripts/earnings/builder_adapters.py scripts/earnings/earnings_orchestrator.py scripts/earnings/render_section.py scripts/earnings/compare_section.py scripts/earnings/concept_fallback_discovery.py scripts/earnings/q4_derivation.py .claude/skills/earnings-orchestrator/scripts/warmup_cache.py
```

#### Stage 1 commit

```bash
cd /home/faisal/em-builders-restructure
git add scripts/earnings/builders/__init__.py \
        scripts/earnings/builders/_paths.py \
        scripts/earnings/test_builders_paths.py
git commit -m "feat(builders): create scripts/earnings/builders package skeleton + _paths helper (commit 1/20)"
```

#### Stage 1 rollback: `git revert HEAD`

---

### Stages 2–13 — File moves (12 commits, 6 COPY + 6 SHIM pairs)

Each move follows a strict 2-commit pattern:

- **COPY commit** (even-numbered stage): copy the file's body into the canonical location with `_paths.py` integration. The OLD file at the OLD path is UNTOUCHED — production still uses old.
- **SHIM commit** (odd-numbered stage): replace the OLD file with a tiny shim that re-exports the canonical via `globals().update()`. After this commit, OLD and NEW are identity-equal; production routes through the shim.

**Why the 2-step pattern is safer than my single-commit approach:** between the COPY and SHIM commits, you can run integration tests and packet-level comparisons against BOTH old and new locations. If new diverges, you revert the SHIM commit (or just don't apply it) and keep the canonical copy for further investigation. With a single-commit move, you lose this differential.

#### Move order (smallest blast radius first)

| Stage | File | Why this order |
|---|---|---|
| 2-3 | `peer_earnings_snapshot.py` | Smallest, exercises cross-module `_parse_dt_for_pit` shadow |
| 4-5 | `macro_snapshot.py` | Mid-size, exercises path-math discipline (3 `parents[2]` sites) |
| 6-7 | `consensus.py` | Has `_classifier` singleton (highest-risk identity case) — mechanics now battle-tested |
| 8-9 | `prior_financials.py` | Largest external surface (4 caller sites for private/public helpers) |
| 10-11 | `warmup_cache.py` | Cross-package + .sh wrapper script-target — most novel constraint |
| 12-13 | `adapters.py` | Updates lazy imports to canonical paths — done last so all canonical builders exist |

#### Standard COPY recipe (Stages 2, 4, 6, 8, 10, 12)

1. `cp scripts/earnings/<X>.py scripts/earnings/builders/<new_name>.py` (do NOT use `git mv` — we want both files to coexist after this stage; the OLD becomes a shim only in the next stage)
2. In `scripts/earnings/builders/<new_name>.py`:
   - Replace `sys.path.insert(0, str(Path(__file__).resolve().parents[2]))` AND import the path helpers needed by the file body. Use the **flat-import** style (preferred for clarity — never reach `_paths.X` without an explicit name in scope):
     ```python
     from ._paths import (
         ensure_legacy_paths,
         ENV_PATH,           # only if file uses it
         SCRIPTS_DIR,        # only if file uses it
         SKILL_SCRIPTS_DIR,  # only if file uses it
         skill_script,       # only if file uses skill_script(...)
     )
     ensure_legacy_paths()
     ```
     Drop unused imports from the `from` block — the per-stage instructions in §5–§10 specify exactly which names each builder needs.
   - Replace `Path(__file__).resolve().parents[2] / ".env"` with `ENV_PATH` (now in scope via the import above; do NOT write `_paths.ENV_PATH`).
   - Replace any hardcoded `parents[2] / "scripts"` with `SCRIPTS_DIR`.
   - Replace any hardcoded `parents[2] / ".claude/skills/..."` with `SKILL_SCRIPTS_DIR` (or remove the per-function sys.path insertion entirely, since `ensure_legacy_paths()` already added it).
   - Replace `parents[2] / '.claude/skills/.../pit_fetch.py'` with `skill_script("pit_fetch.py")`.
3. **Add a per-builder mocked unit test file** (Stage-specific section below).
4. Run static guard:
   ```bash
   ! rg -n "parents\[2\]|/home/faisal/EventMarketDB" scripts/earnings/builders/<new_name>.py
   ```
5. **Run copy-integrity review** — diff old vs new and confirm changes are ONLY in the path-setup region:
   ```bash
   git diff --no-index scripts/earnings/<X>.py scripts/earnings/builders/<new_name>.py
   ```
   **Expected diff hunks (and ONLY these):**
   - Path-setup line(s) replaced by an explicit flat-import block: `from ._paths import ensure_legacy_paths, ENV_PATH, SCRIPTS_DIR, SKILL_SCRIPTS_DIR, skill_script` (drop unused names) + a single `ensure_legacy_paths()` call
   - `.env` references replaced with bare `ENV_PATH` (NOT `_paths.ENV_PATH` — the flat-import style brings the name directly into module scope; using `_paths.X` would require `from . import _paths` which the COPY recipe forbids)
   - skill-script path references replaced with bare `skill_script(...)` or `SKILL_SCRIPTS_DIR`
   - `scripts/` directory references replaced with bare `SCRIPTS_DIR`
   - Per-function legacy `sys.path.insert(0, ...)` blocks DELETED (not just commented out — they're now no-ops covered by `ensure_legacy_paths()`)
   - **Stage 12 (adapters.py) ONLY:** lazy imports inside adapter functions point to canonical modules (e.g. `from scripts.earnings.builders.consensus import build_consensus as _legacy`)

   **Anything else is a red flag** — investigate before committing. The COPY stage is mechanical; function bodies, signatures, schema fields, default output paths, retry logic, and stdout/stderr behavior MUST be byte-identical to the source file.

#### Standard SHIM recipe (Stages 3, 5, 7, 9, 11, 13)

1. Replace `scripts/earnings/<X>.py` (or `.claude/.../warmup_cache.py` for Stage 11) with the appropriate shim template from §5.
2. **Extend `MODULE_PAIRS`** in `test_builders_imports.py`:
   ```python
   MODULE_PAIRS["<old_bare>"] = (
       "scripts.earnings.builders.<new_name>",
       ["build_X", "main", ...all symbols including private],
   )
   ```
3. Run identity test — must pass for every newly-listed symbol.

#### Per-stage gate (run BEFORE every stage commit)

```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python

# 1. Identity invariant
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_imports.py -v -x

# 2. Surface inventory
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_surface.py -v -x

# 3. Path helper still good
PYTHONPATH=. $PY -m pytest scripts/earnings/test_builders_paths.py -q

# 4. Renderer baseline (must remain green)
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_renderer_*.py -q

# 5. Orchestrator inline self-test — PLUMBING ONLY (NOT builder end-to-end proof).
#    `--test` exercises orchestrator/rendering wiring; it does NOT prove that
#    each of the 7 build_*() functions returns the right packet for a real
#    ticker. Builder behavior is verified by:
#      - per-stage mocked unit tests (this gate, step 7)
#      - mandatory live integration in §12 (test_adapter_validation +
#        test_builder_validation against ticker FIVE)
PYTHONPATH=scripts/earnings $PY scripts/earnings/earnings_orchestrator.py --test

# 6. CLI smoke (--test rows are load-bearing)
PYTHONPATH=scripts/earnings $PY -m pytest \
    scripts/earnings/test_builders_cli_smoke.py::test_cli_warmup_cache_test_flag \
    scripts/earnings/test_builders_cli_smoke.py::test_cli_warmup_cache_sh_test_flag \
    -v
    # NOTE: these two rows are NOT marked @pytest.mark.live — they invoke
    # warmup_cache.py --test which runs the in-process regression suite (no
    # external services). Do NOT add `-m live` here; that would deselect them.

# 7. Stage-specific mocked unit test file (added in COPY stage)
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_<X>.py -v

# 8. Consumer-import smoke
PYTHONPATH=scripts/earnings $PY -c "import earnings_orchestrator"
PYTHONPATH=scripts/earnings $PY -c "import concept_fallback_discovery"
PYTHONPATH=scripts/earnings $PY -c "import q4_derivation"

# 9. Safety: main is untouched
cd /home/faisal/EventMarketDB && git status -s -- scripts/earnings/build_consensus.py scripts/earnings/build_prior_financials.py scripts/earnings/macro_snapshot.py scripts/earnings/peer_earnings_snapshot.py scripts/earnings/builder_adapters.py scripts/earnings/earnings_orchestrator.py scripts/earnings/render_section.py scripts/earnings/compare_section.py scripts/earnings/concept_fallback_discovery.py scripts/earnings/q4_derivation.py .claude/skills/earnings-orchestrator/scripts/warmup_cache.py
```

Only after all 9 checks are green does the stage commit. If any fails, fix in place; do NOT commit.

---

### Stage 2 — COPY `peer_earnings_snapshot.py` canonically (1 commit)

#### Files changed
```text
scripts/earnings/builders/peer_earnings_snapshot.py
scripts/earnings/test_builders_peer_snapshot.py
```

#### Edit A — `scripts/earnings/builders/peer_earnings_snapshot.py`

Copy from `scripts/earnings/peer_earnings_snapshot.py`. Replace:

```python
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
```

with:

```python
from ._paths import ensure_legacy_paths
ensure_legacy_paths()
```

Otherwise function bodies unchanged.

#### Edit B — Mocked unit tests `scripts/earnings/test_builders_peer_snapshot.py`

```python
"""Mocked unit tests for scripts.earnings.builders.peer_earnings_snapshot.
Deterministic — no live Neo4j calls. Live integration is covered by the
existing test_builder_validation.py harness (opt-in).
"""
from __future__ import annotations
from unittest.mock import patch, MagicMock
import json
import os
import tempfile

from scripts.earnings.builders import peer_earnings_snapshot as ps


def test_no_rows_returns_empty_peers_packet():
    """Mock get_manager to return empty rows; assert packet shape + empty peers."""
    mock_manager = MagicMock()
    mock_manager.execute_cypher_query_all.return_value = []
    with patch.object(ps, "get_manager", return_value=mock_manager):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            out_path = f.name
        try:
            packet = ps.build_peer_earnings_snapshot(
                ticker="CRM",
                pit_cutoff="2024-09-15T16:00:00+00:00",
                out_path=out_path,
            )
            assert packet["schema_version"] == "peer_earnings_snapshot.v1"
            assert packet.get("peers", []) == []
            assert "pit_cutoff" in packet
            assert os.path.exists(out_path)
        finally:
            os.unlink(out_path)


def test_parse_dt_for_pit_handles_z_suffix():
    """The Z timestamp suffix must parse to UTC datetime."""
    from datetime import timezone
    dt = ps._parse_dt_for_pit("2024-09-15T16:00:00Z")
    assert dt.tzinfo is not None
    assert dt.utcoffset() == timezone.utc.utcoffset(dt)


def test_render_text_accepts_valid_packet():
    packet = {
        "schema_version": "peer_earnings_snapshot.v1",
        "ticker": "CRM",
        "pit_cutoff": "2024-09-15T16:00:00+00:00",
        "peers": [],
    }
    text = ps.render_text(packet)
    assert isinstance(text, str)
    assert len(text) > 0
```

#### Stage 2 verification

```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
$PY -m py_compile scripts/earnings/builders/peer_earnings_snapshot.py
! rg -n "parents\[2\]|/home/faisal/EventMarketDB" scripts/earnings/builders/peer_earnings_snapshot.py && echo "path math clean"
PYTHONPATH=. $PY -m pytest scripts/earnings/test_builders_peer_snapshot.py -v
# Run standard per-stage gate (omit identity test until Stage 3)
```

Optional integration:
```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
$PY -m scripts.earnings.builders.peer_earnings_snapshot AVGO \
  --pit 2023-12-07T16:18:51-05:00 \
  --out-path /tmp/builders_new_peers.json
diff <(jq -S 'del(.assembled_at) | .gaps |= sort' /tmp/builders_baseline/peer_earnings_avgo.json) \
     <(jq -S 'del(.assembled_at) | .gaps |= sort' /tmp/builders_new_peers.json)
# expect: empty diff (or only documented deltas)
```

#### Stage 2 commit
```bash
cd /home/faisal/em-builders-restructure
git add scripts/earnings/builders/peer_earnings_snapshot.py scripts/earnings/test_builders_peer_snapshot.py
git commit -m "refactor(builders): copy peer_earnings_snapshot canonically + mocked tests (commit 2/20)"
```

---

### Stage 3 — SHIM old `peer_earnings_snapshot.py` (1 commit)

#### Files changed
```text
scripts/earnings/peer_earnings_snapshot.py    (replaced with shim)
scripts/earnings/test_builders_imports.py     (extend MODULE_PAIRS)
```

#### Edit A — Replace `scripts/earnings/peer_earnings_snapshot.py` with the shim template from §5.1.

#### Edit B — Extend `MODULE_PAIRS`

```python
MODULE_PAIRS["peer_earnings_snapshot"] = (
    "scripts.earnings.builders.peer_earnings_snapshot",
    ["build_peer_earnings_snapshot", "render_text", "main", "_parse_dt_for_pit"],
)
```

#### Stage 3 gate (standard) + extra:

```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
$PY -m py_compile scripts/earnings/peer_earnings_snapshot.py
PYTHONPATH=scripts/earnings $PY -c "from peer_earnings_snapshot import _parse_dt_for_pit; print(_parse_dt_for_pit)"
$PY scripts/earnings/peer_earnings_snapshot.py AVGO \
  --pit 2023-12-07T16:18:51-05:00 \
  --out-path /tmp/builders_old_peers_after_shim.json
```

#### Stage 3 commit
```bash
cd /home/faisal/em-builders-restructure
git add scripts/earnings/peer_earnings_snapshot.py scripts/earnings/test_builders_imports.py
git commit -m "refactor(builders): shim old peer_earnings_snapshot.py — identity verified (commit 3/20)"
```

---

### Stage 4 — COPY `macro_snapshot.py` canonically (1 commit)

#### Files changed
```text
scripts/earnings/builders/macro_snapshot.py
scripts/earnings/test_builders_macro_snapshot.py
```

#### Edit A — `scripts/earnings/builders/macro_snapshot.py`

Copy from old. Replace:

```python
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
```

with:

```python
from ._paths import ensure_legacy_paths, ENV_PATH, skill_script
ensure_legacy_paths()
PIT_FETCH = skill_script("pit_fetch.py")
```

Replace `_load_polygon_key`'s `Path(__file__).resolve().parents[2] / '.env'` with `ENV_PATH`.

#### Edit B — `scripts/earnings/test_builders_macro_snapshot.py`

```python
"""Mocked unit tests for scripts.earnings.builders.macro_snapshot."""
from __future__ import annotations
from unittest.mock import patch, MagicMock
import os, tempfile

from scripts.earnings.builders import macro_snapshot as ms


def test_yahoo_source_uses_yahoo_helpers():
    """Mock _yahoo_daily/_yahoo_minute (return list[dict] of bars, not scalars)
    AND yfinance.Ticker (used directly inside _compute_spy_now around line 445)
    AND subprocess.run (the pit_fetch invocation for Benzinga headlines).

    Verified at scripts/earnings/macro_snapshot.py:115 — `def _yahoo_daily(...) -> list[dict]:`
    with bar shape {date, open, high, low, close, volume}; line 141 — `_yahoo_minute(...) -> list[dict]:`
    with shape {ts_ms, ts_iso, open, high, low, close, volume}.
    """
    daily_bars = [
        {"date": "2024-09-13", "open": 99.0, "high": 100.5, "low": 98.5,
         "close": 100.0, "volume": 1_000_000},
    ]
    minute_bars = [
        {"ts_ms": 1726425600000, "ts_iso": "2024-09-15T16:00:00Z",
         "open": 100.0, "high": 100.5, "low": 99.5, "close": 100.5, "volume": 100_000},
    ]
    fake_yf_ticker = MagicMock()
    fake_yf_ticker.info = {"regularMarketPrice": 5500.0}
    fake_yf_ticker.history.return_value = MagicMock(empty=True)  # safe default
    # macro_snapshot.py:448 calls `yf.Ticker('^VIX').fast_info.last_price` in
    # live mode. Without an explicit float here, MagicMock's auto-attribute
    # returns ANOTHER MagicMock; `float(MagicMock())` raises TypeError; the
    # bare `except Exception` at line 463 swallows it; vix_level stays None and
    # a `missing_vix` gap is appended. The test "passes" but never exercises
    # the VIX-success branch. Setting an explicit float makes the path real.
    fake_yf_ticker.fast_info.last_price = 20.0
    # Configure the manager mock explicitly: macro_snapshot.py calls
    # manager.execute_cypher_query_all(...) for sector lookup. A bare
    # `MagicMock()` would let that call return a MagicMock object that
    # could end up in packet fields and silently break json.dump.
    mock_manager = MagicMock()
    mock_manager.execute_cypher_query_all.return_value = []
    with patch.object(ms, "_yahoo_daily", return_value=daily_bars) as yd, \
         patch.object(ms, "_yahoo_minute", return_value=minute_bars) as ym, \
         patch.object(ms, "get_manager", return_value=mock_manager), \
         patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="[]", stderr="")), \
         patch("yfinance.Ticker", return_value=fake_yf_ticker):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            out = f.name
        try:
            packet = ms.build_macro_snapshot(
                ticker="CRM",
                pit_cutoff="2024-09-15T16:00:00+00:00",
                market_session="post_market",
                source="yahoo",
                out_path=out,
            )
            assert packet["schema_version"].startswith("macro_snapshot.v")
            assert os.path.exists(out)
            assert yd.called or ym.called
        finally:
            os.unlink(out)


def test_render_text_accepts_packet():
    packet = {
        "schema_version": "macro_snapshot.v2",
        "ticker": "CRM",
        "pit_cutoff": "2024-09-15T16:00:00+00:00",
        "spy": {"close": 5500.0},
        "indicators": {},
        "headlines": [],
    }
    text = ms.render_text(packet)
    assert isinstance(text, str)


def test_pit_fetch_resolves_correctly():
    """Verify PIT_FETCH path is computed via _paths.skill_script and exists."""
    assert os.path.exists(ms.PIT_FETCH)
    assert ms.PIT_FETCH.endswith("pit_fetch.py")
```

#### Stage 4 gate (standard COPY pattern)

#### Stage 4 commit
```bash
cd /home/faisal/em-builders-restructure
git add scripts/earnings/builders/macro_snapshot.py scripts/earnings/test_builders_macro_snapshot.py
git commit -m "refactor(builders): copy macro_snapshot canonically + mocked tests (commit 4/20)"
```

---

### Stage 5 — SHIM old `macro_snapshot.py` (1 commit)

#### Edit A — Replace `scripts/earnings/macro_snapshot.py` with shim template §5.1.

#### Edit B — Extend `MODULE_PAIRS`
```python
MODULE_PAIRS["macro_snapshot"] = (
    "scripts.earnings.builders.macro_snapshot",
    ["build_macro_snapshot", "render_text", "main"],
)
```

#### Stage 5 gate (standard) + extra
```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
$PY scripts/earnings/macro_snapshot.py AVGO \
  --pit 2023-12-07T16:18:51-05:00 \
  --session post_market \
  --source yahoo \
  --out-path /tmp/builders_old_macro_after_shim.json
```

#### Stage 5 commit
```bash
cd /home/faisal/em-builders-restructure
git add scripts/earnings/macro_snapshot.py scripts/earnings/test_builders_imports.py
git commit -m "refactor(builders): shim old macro_snapshot.py — identity verified (commit 5/20)"
```

---

### Stage 6 — COPY `build_consensus.py` → `builders/consensus.py` canonically (1 commit)

This is the **module-level singleton risk case**. `build_consensus._classifier` (line 131) is a module-level `None` initialized lazily by `_get_classifier()`. Risk-mitigation tests added.

#### Files changed
```text
scripts/earnings/builders/consensus.py
scripts/earnings/test_builders_consensus.py
```

#### Edit A — `scripts/earnings/builders/consensus.py`

Copy from `scripts/earnings/build_consensus.py`. The top-of-file imports become:

```python
from ._paths import ensure_legacy_paths, ENV_PATH, SCRIPTS_DIR, SKILL_SCRIPTS_DIR
ensure_legacy_paths()
```

Then DELETE every legacy path-math construct in the file body. The known sites:

- **Line 35** `sys.path.insert(0, str(Path(__file__).resolve().parents[2]))` — DELETE; replaced by the top-of-file `ensure_legacy_paths()`.
- **Line 71** inside `_load_env`: replace `env_path = Path(__file__).resolve().parents[2] / ".env"` with `env_path = ENV_PATH`.
- **`_get_fye_month()` (around line 252):** locate the block `scripts_dir = Path(__file__).resolve().parents[2] / "scripts"` and the surrounding conditional `sys.path.insert(0, str(scripts_dir))`. DELETE both. `ensure_legacy_paths()` already added `SCRIPTS_DIR` so the bare `from sec_quarter_cache_loader import refresh_ticker` works.
- **`_build_quarter_ends()` (around line 299):** locate the block `_fm_dir = Path(__file__).resolve().parents[2] / ".claude/skills/earnings-orchestrator/scripts"` and the conditional sys.path insertion. DELETE both. `ensure_legacy_paths()` already added `SKILL_SCRIPTS_DIR`.
- **`_map_yahoo_periods_to_fdes()` (around line 344):** identical pattern to `_build_quarter_ends()` — DELETE the temporary `_fm_dir` + sys.path insertion block.

The static guard `! rg -n "parents\[2\]|/home/faisal/EventMarketDB" scripts/earnings/builders/consensus.py` MUST return zero matches after these edits. If any remain, the deletion was incomplete.

#### Edit B — `scripts/earnings/test_builders_consensus.py`

```python
"""Mocked unit tests for scripts.earnings.builders.consensus."""
from __future__ import annotations
from unittest.mock import patch, MagicMock
import os, tempfile, pytest

from scripts.earnings.builders import consensus as bc


def test_no_api_key_raises():
    """Without ALPHAVANTAGE_API_KEY, build_consensus must raise RuntimeError."""
    with patch.dict(os.environ, {}, clear=True), \
         patch.object(bc, "_load_env", return_value=None):
        with pytest.raises(RuntimeError, match="ALPHAVANTAGE_API_KEY"):
            bc.build_consensus(ticker="CRM", quarter_info={"period_of_report": "2024-09-30"})


def test_historical_mode_no_forward_estimates():
    """Historical PIT mode must return empty forward_estimates and add pit_excluded gap."""
    # _fetch_all_av returns a TUPLE of three AV JSON responses:
    #   (EARNINGS, EARNINGS_ESTIMATES, INCOME_STATEMENT)
    # Verified at scripts/earnings/build_consensus.py:182 — `def _fetch_all_av(...) -> tuple:`
    # and line 203 `return tuple(results)`. Returning a dict would crash the consumer.
    fake_av = (
        {"quarterlyEarnings": []},
        {"data": []},
        {"quarterlyReports": []},
    )
    with patch.object(bc, "_load_env", return_value=None), \
         patch.dict(os.environ, {"ALPHAVANTAGE_API_KEY": "fake_key"}), \
         patch.object(bc, "_fetch_all_av", return_value=fake_av), \
         patch.object(bc, "_get_fye_month", return_value=12):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            out = f.name
        try:
            packet = bc.build_consensus(
                ticker="CRM",
                quarter_info={"period_of_report": "2024-09-30"},
                as_of_ts="2024-09-15T16:00:00+00:00",
                out_path=out,
            )
            assert packet["forward_estimates"] == []
            assert any("pit_excluded" in str(g) for g in packet.get("gaps", []))
        finally:
            os.unlink(out)


def test_parse_iso_handles_z_naive_invalid():
    from datetime import datetime
    assert bc._parse_iso("2024-09-15T16:00:00Z") is not None
    assert bc._parse_iso("2024-09-15T16:00:00") is not None    # naive
    assert bc._parse_iso("garbage") is None


def test_classifier_singleton_within_canonical_module():
    """First call initializes; second returns same instance."""
    cls1 = bc._get_classifier()
    cls2 = bc._get_classifier()
    assert cls1 is cls2
```

#### Stage 6 gate (standard COPY pattern)

#### Stage 6 commit
```bash
cd /home/faisal/em-builders-restructure
git add scripts/earnings/builders/consensus.py scripts/earnings/test_builders_consensus.py
git commit -m "refactor(builders): copy build_consensus to consensus.py canonically + mocked tests (commit 6/20)"
```

---

### Stage 7 — SHIM old `build_consensus.py` + classifier-singleton identity guard (1 commit)

#### Edit A — Replace `scripts/earnings/build_consensus.py` with shim template §5.1 (`_impl = consensus`).

#### Edit B — Extend `MODULE_PAIRS`
```python
MODULE_PAIRS["build_consensus"] = (
    "scripts.earnings.builders.consensus",
    ["build_consensus", "main", "_parse_iso", "_normalize_session"],
)
```

#### Edit C — Add singleton guard to `test_builders_imports.py`

```python
def test_classifier_singleton_across_paths():
    """build_consensus._classifier must be one cell across all import paths.
    If this fails, the module loaded twice and the lazy singleton split."""
    import build_consensus as a
    import scripts.earnings.build_consensus as b
    import scripts.earnings.builders.consensus as c
    cls_a = a._get_classifier()
    cls_b = b._get_classifier()
    cls_c = c._get_classifier()
    # All three import paths must dispatch to the canonical _get_classifier
    # AND return the same singleton object.
    assert cls_a is cls_b is cls_c, (
        f"singleton split: a={id(cls_a)}, b={id(cls_b)}, c={id(cls_c)}"
    )
    # And the canonical module's _classifier global must point at the same
    # object (it's the cell that _get_classifier mutates via `global _classifier`).
    assert cls_a is c._classifier, "canonical module's _classifier mutation not visible from shim"
```

#### Stage 7 gate (standard) + the singleton test

#### Stage 7 commit
```bash
cd /home/faisal/em-builders-restructure
git add scripts/earnings/build_consensus.py scripts/earnings/test_builders_imports.py
git commit -m "refactor(builders): shim old build_consensus + classifier-singleton guard (commit 7/20)"
```

---

### Stage 8 — COPY `build_prior_financials.py` → `builders/prior_financials.py` canonically (1 commit)

#### Files changed
```text
scripts/earnings/builders/prior_financials.py
scripts/earnings/test_builders_prior_financials.py
```

#### Edit A — `scripts/earnings/builders/prior_financials.py`

Copy from old. The top-of-file imports become:

```python
from ._paths import ensure_legacy_paths, ENV_PATH, SCRIPTS_DIR
ensure_legacy_paths()
```

(All names used inside the file MUST be imported explicitly — `_paths.ENV_PATH`
is NOT in scope unless `from . import _paths` is also added; we prefer the
flat import style for clarity.)

Then make these specific replacements throughout the file body:

- **Line 34** `sys.path.insert(0, str(Path(__file__).resolve().parents[2]))` — DELETE; replaced by the `ensure_legacy_paths()` call above.
- **Lines 37–39** `_FM_DIR = Path(__file__).resolve().parents[2] / ".claude/skills/earnings-orchestrator/scripts"` plus the conditional `sys.path.insert(0, _FM_DIR)` block — DELETE entirely; not needed because `ensure_legacy_paths()` already added `SKILL_SCRIPTS_DIR` to sys.path with the correct precedence.
- **Line 165** inside `_load_env`: replace `env_path = Path(__file__).resolve().parents[2] / ".env"` with `env_path = ENV_PATH`.
- **Line 272** inside `_get_fye_month`: replace the `scripts_dir = Path(__file__).resolve().parents[2] / "scripts"` block + its conditional `sys.path.insert(0, scripts_dir)` with NOTHING (delete both lines). Reason: `ensure_legacy_paths()` already added `SCRIPTS_DIR` to sys.path. If the original code wraps the import in `try/finally` to clean up, drop the cleanup too — leaving `SCRIPTS_DIR` permanently on sys.path is the new contract.

The lazy outbound import at line 1593 (`from xbrl_exact_splits import ...`) continues to work because `ensure_legacy_paths()` adds `EARNINGS_DIR` to sys.path.

After the edits, run the static guard (Section 6) and verify no remaining
`parents[2]` or hardcoded `/home/faisal/EventMarketDB` references exist in
the new file.

#### Edit B — `scripts/earnings/test_builders_prior_financials.py`

```python
"""Mocked unit tests for scripts.earnings.builders.prior_financials."""
from __future__ import annotations
from unittest.mock import patch, MagicMock
import os, tempfile

from scripts.earnings.builders import prior_financials as bpf


def test_classify_period_quarter():
    res = bpf.classify_period("2024-07-01", "2024-09-30")
    # ~92 days = quarter (Q3 calendar)
    assert res in ("Q1", "Q2", "Q3", "Q4")


def test_classify_period_year():
    res = bpf.classify_period("2024-01-01", "2024-12-31")
    assert res == "FY"


def test_is_target_period_true_when_match():
    assert bpf.is_target_period("2024-09-30", "2024-09-30") is True


def test_is_target_period_false_when_mismatch():
    assert bpf.is_target_period("2024-06-30", "2024-09-30") is False


def test_parse_value_numeric():
    assert bpf._parse_value(1234.5) == 1234.5
    assert bpf._parse_value("1234.5") == 1234.5


def test_parse_value_none():
    assert bpf._parse_value(None) is None
    assert bpf._parse_value("") is None
    assert bpf._parse_value("garbage") is None


def test_revenue_splits_sidecar_error_adds_gap():
    """If xbrl_exact_splits raises, builder must add a revenue_splits_error gap.

    NOTE: get_manager is imported LOCALLY inside build_prior_financials() at
    line 1286 (and main() at line 1721) — there is NO module-level
    `bpf.get_manager` attribute. Therefore patch.object(bpf, "get_manager")
    fails with AttributeError. The correct patch target is the SOURCE module:
    `neograph.Neo4jConnection.get_manager`.

    Also: the revenue-splits error path is best tested by calling the helper
    `_build_revenue_splits_section` directly. Driving it through a full
    build_prior_financials invocation requires too much Neo4j mocking to be
    reliable.
    """
    gaps: list = []
    quarters = [{"period": "2024-09-30", "fiscal_label": "FY2024 Q3"}]
    with patch("xbrl_exact_splits.extract_segment_splits",
               side_effect=RuntimeError("boom")):
        result = bpf._build_revenue_splits_section(
            "CRM", "2024-09-30", "...", quarters, gaps,
        )
    # Helper returns None on error AND appends a gap of the documented type.
    assert result is None
    assert any(g.get("type") == "revenue_splits_error" for g in gaps), gaps


def test_get_manager_is_locally_imported_inside_build_function():
    """Sanity guard for the patch-target choice above. If a future refactor
    hoists get_manager to module level, this test will fail and the mocked
    test above can switch to patch.object(bpf, "get_manager")."""
    import inspect
    # get_manager must NOT be a module-level attribute of bpf
    assert not hasattr(bpf, "get_manager"), (
        "get_manager is now a module-level attribute — update the patch target "
        "in test_revenue_splits_sidecar_error_adds_gap accordingly."
    )
    # And the import statement should appear inside build_prior_financials's source
    src = inspect.getsource(bpf.build_prior_financials)
    assert "from neograph.Neo4jConnection import get_manager" in src
```

#### Stage 8 gate (standard) + extra:

The standard per-stage gate (§10) covers the mocked + non-live checks. The
two extras below have different live-service profiles:

```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python

# NON-LIVE: pure mocked unit tests (run in every per-stage gate)
$PY -m pytest \
    scripts/earnings/test_builders_prior_financials.py \
    scripts/earnings/test_q4_derivation.py \
    -q
```

```bash
# LIVE-SERVICE: these tests directly invoke build_prior_financials() against
# Neo4j (test_revenue_splits_integration.py:24 calls the real builder; verified
# at scripts/earnings/test_revenue_splits_integration.py:12 — bare import
# `from build_prior_financials import build_prior_financials`). DO NOT run in
# per-stage gates. Run ONLY in the §12 final integration window OR opt-in via
# RUN_LIVE_BUILDER_CLI=1.
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
if [ "${RUN_LIVE_BUILDER_CLI:-0}" = "1" ]; then
  $PY -m pytest \
      scripts/earnings/test_xbrl_exact_splits.py \
      scripts/earnings/test_revenue_splits_integration.py \
      -q
else
  echo "[skipped] live tests — set RUN_LIVE_BUILDER_CLI=1 to run, or rely on §12 final integration"
fi
```

#### Stage 8 commit
```bash
cd /home/faisal/em-builders-restructure
git add scripts/earnings/builders/prior_financials.py scripts/earnings/test_builders_prior_financials.py
git commit -m "refactor(builders): copy build_prior_financials to prior_financials.py canonically + mocked tests (commit 8/20)"
```

---

### Stage 9 — SHIM old `build_prior_financials.py` + xbrl lazy-import guard (1 commit)

#### Edit A — Replace `scripts/earnings/build_prior_financials.py` with shim template §5.1.

#### Edit B — Extend `MODULE_PAIRS`
```python
MODULE_PAIRS["build_prior_financials"] = (
    "scripts.earnings.builders.prior_financials",
    ["build_prior_financials", "classify_period", "is_target_period",
     "dedupe_facts", "main", "_parse_value", "METRIC_REGISTRY"],
)
```

#### Edit C — Add xbrl lazy-import guard to `test_builders_imports.py`

```python
def test_xbrl_exact_splits_lazy_import_works():
    """build_prior_financials.py:1593 lazily imports xbrl_exact_splits — must
    keep working from the new builders/ location."""
    import xbrl_exact_splits
    assert hasattr(xbrl_exact_splits, "extract_segment_splits")
    assert hasattr(xbrl_exact_splits, "build_revenue_splits_section")
```

#### Stage 9 gate (standard) + extras:
```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
PYTHONPATH=scripts/earnings $PY -c "from build_prior_financials import _parse_value; print(_parse_value)"
PYTHONPATH=scripts/earnings $PY -c "from q4_derivation import classify_period, is_target_period; print('q4_derivation imports OK')"
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_build_prior_financials_regression.py -q
```

#### Stage 9 commit
```bash
cd /home/faisal/em-builders-restructure
git add scripts/earnings/build_prior_financials.py scripts/earnings/test_builders_imports.py
git commit -m "refactor(builders): shim old build_prior_financials + xbrl lazy-import guard (commit 9/20)"
```

---

### Stage 10 — COPY `warmup_cache.py` canonically (1 commit)

#### Files changed
```text
scripts/earnings/builders/warmup_cache.py
scripts/earnings/test_builders_warmup_cache.py
```

#### Edit A — `scripts/earnings/builders/warmup_cache.py`

Copy from `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py`. Replace:
```python
sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts")
sys.path.insert(0, "/home/faisal/EventMarketDB")
```
with:
```python
from ._paths import ensure_legacy_paths
ensure_legacy_paths()
```

All other code unchanged. Every CLI mode and `/tmp` output path preserved:
- `/tmp/concept_cache_{TICKER}.json`
- `/tmp/member_cache_{TICKER}.json`
- `/tmp/member_map_{TICKER}.json`
- `/tmp/transcript_content_{TRANSCRIPT_ID}.json`
- `/tmp/mda_content_{ACCESSION}.json`
- `/tmp/8k_content_{ACCESSION}.json`
- `/tmp/earnings_8k_packet_{ACCESSION}.json`
- `/tmp/earnings_guidance_{TICKER}.json`
- `/tmp/earnings_inter_quarter_{TICKER}.json`

#### Edit B — `scripts/earnings/test_builders_warmup_cache.py`

```python
"""Tests for scripts.earnings.builders.warmup_cache."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Use the running interpreter; `git worktree add` does NOT carry venv/.
PY = sys.executable


def test_module_test_flag_passes():
    """`python -m scripts.earnings.builders.warmup_cache --test` runs internal regression."""
    import os
    res = subprocess.run(
        [PY, "-m", "scripts.earnings.builders.warmup_cache", "--test"],
        capture_output=True, text=True, timeout=60,
        # Explicit value AFTER **os.environ so it overrides any inherited PYTHONPATH.
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    assert res.returncode == 0, f"--test failed: {res.stderr}"


def test_import_surface_complete():
    """All public + private symbols listed in EXPECTED_SURFACE['warmup_cache'] are reachable."""
    from scripts.earnings.builders import warmup_cache as wc
    expected = [
        "build_8k_packet", "build_guidance_history", "build_inter_quarter_context",
        "render_guidance_text", "render_inter_quarter_text",
        "run_warmup", "run_transcript", "run_mda", "run_8k", "main",
        "_parse_dt_for_pit", "_run_v2_regression_tests",
    ]
    for sym in expected:
        assert hasattr(wc, sym), f"warmup_cache missing {sym}"
```

#### Stage 10 gate (standard) + extra:
```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
$PY -m scripts.earnings.builders.warmup_cache --test
```

#### Stage 10 commit
```bash
cd /home/faisal/em-builders-restructure
git add scripts/earnings/builders/warmup_cache.py scripts/earnings/test_builders_warmup_cache.py
git commit -m "refactor(builders): copy warmup_cache canonically + module test (commit 10/20)"
```

---

### Stage 11 — SHIM old `.claude/.../warmup_cache.py` + cross-module shadow guard (1 commit)

#### Edit A — Replace `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py` with shim template §5.3 (uses `parents[4]`).

#### Edit B — `warmup_cache.sh` UNCHANGED

#### Edit C — Extend `MODULE_PAIRS`

```python
MODULE_PAIRS["warmup_cache"] = (
    "scripts.earnings.builders.warmup_cache",
    ["run_warmup", "run_transcript", "run_mda", "run_8k",
     "build_8k_packet", "build_guidance_history", "build_inter_quarter_context",
     "render_guidance_text", "render_inter_quarter_text",
     "_parse_dt_for_pit", "_run_v2_regression_tests", "main"],
)
```

#### Edit D — Add shadow-disambiguation guard to `test_builders_imports.py`

```python
def test_parse_dt_for_pit_disambiguation():
    """_parse_dt_for_pit exists in TWO modules with DIFFERENT functions —
    each module's import paths resolve to its own function, never the other's."""
    import warmup_cache, peer_earnings_snapshot
    import scripts.earnings.builders.warmup_cache as wc_new
    import scripts.earnings.builders.peer_earnings_snapshot as pe_new
    # Within-module identity:
    assert warmup_cache._parse_dt_for_pit is wc_new._parse_dt_for_pit
    assert peer_earnings_snapshot._parse_dt_for_pit is pe_new._parse_dt_for_pit
    # Cross-module distinctness:
    assert warmup_cache._parse_dt_for_pit is not peer_earnings_snapshot._parse_dt_for_pit
```

#### Stage 11 gate (standard) + extras

```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
$PY .claude/skills/earnings-orchestrator/scripts/warmup_cache.py --test
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh --test
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_imports.py scripts/earnings/test_builders_warmup_cache.py -v
```

#### Stage 11 commit
```bash
cd /home/faisal/em-builders-restructure
git add .claude/skills/earnings-orchestrator/scripts/warmup_cache.py \
        scripts/earnings/test_builders_imports.py
git commit -m "refactor(builders): shim old warmup_cache + cross-module shadow guard (commit 11/20)"
```

---

### Stage 12 — COPY `builder_adapters.py` → `builders/adapters.py` canonically + canonicalize lazy imports (1 commit)

#### Files changed
```text
scripts/earnings/builders/adapters.py
scripts/earnings/builders/__init__.py        # extend with 7 adapter re-exports
scripts/earnings/test_builders_adapters.py
```

#### Edit A — `scripts/earnings/builders/adapters.py`

Copy from `scripts/earnings/builder_adapters.py`. Replace:
```python
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "scripts/earnings"))
sys.path.insert(0, str(_PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"))
```
with:
```python
from ._paths import ensure_legacy_paths
ensure_legacy_paths()
```

**Update lazy imports inside each adapter function** to canonical paths:
```python
def build_8k_packet(...):
    from scripts.earnings.builders.warmup_cache import build_8k_packet as _legacy
    ...

def build_guidance_history(...):
    from scripts.earnings.builders.warmup_cache import build_guidance_history as _legacy
    ...

def build_inter_quarter_context(...):
    from scripts.earnings.builders.warmup_cache import build_inter_quarter_context as _legacy
    ...

def build_peer_earnings_snapshot(...):
    from scripts.earnings.builders.peer_earnings_snapshot import build_peer_earnings_snapshot as _legacy
    ...

def build_macro_snapshot(...):
    from scripts.earnings.builders.macro_snapshot import build_macro_snapshot as _legacy
    ...

def build_consensus(...):
    from scripts.earnings.builders.consensus import build_consensus as _legacy
    ...

def build_prior_financials(...):
    from scripts.earnings.builders.prior_financials import build_prior_financials as _legacy
    ...
```

**Keep imports lazy** (do not hoist to module top); preserves startup side-effect timing.

Preserve `_SuppressStdout`, `_enrich_packet`, `_write_enriched`, `_ensure_dir`, `_derive_mode`, `_now_iso` unchanged.

#### Edit B — Extend `scripts/earnings/builders/__init__.py`

```python
from .adapters import (
    build_8k_packet,
    build_guidance_history,
    build_inter_quarter_context,
    build_peer_earnings_snapshot,
    build_macro_snapshot,
    build_consensus,
    build_prior_financials,
)

__all__ = [
    "build_8k_packet",
    "build_guidance_history",
    "build_inter_quarter_context",
    "build_peer_earnings_snapshot",
    "build_macro_snapshot",
    "build_consensus",
    "build_prior_financials",
]
```

#### Edit C — `scripts/earnings/test_builders_adapters.py`

```python
"""Tests for scripts.earnings.builders.adapters."""
from __future__ import annotations
from unittest.mock import patch, MagicMock
import json, os, tempfile, pytest

from scripts.earnings.builders import adapters as A


def test_contract_fields_present():
    """Every adapter result must include schema_version, ticker, pit_cutoff, source_mode, effective_cutoff_ts."""
    with patch("scripts.earnings.builders.warmup_cache.build_8k_packet"), \
         patch("builtins.open", create=True), \
         patch("json.load", return_value={"schema_version": "8k_packet.v1", "ticker": "CRM"}):
        # Use minimal mock to validate contract enrichment logic only
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            out = f.name
        os.unlink(out)
        # Skip the full call; just test _enrich_packet
        packet = {"schema_version": "8k_packet.v1", "ticker": "CRM"}
        enriched = A._enrich_packet(packet, pit_cutoff="2024-09-15T16:00:00+00:00",
                                     effective_cutoff_ts=None)
        assert enriched["pit_cutoff"] == "2024-09-15T16:00:00+00:00"
        assert enriched["source_mode"] == "historical"
        assert "effective_cutoff_ts" in enriched


def test_8k_packet_catches_systemexit():
    """If legacy raises SystemExit, adapter must raise ValueError."""
    with patch("scripts.earnings.builders.warmup_cache.build_8k_packet", side_effect=SystemExit(1)):
        with pytest.raises(ValueError, match="8-K not found"):
            A.build_8k_packet(
                ticker="CRM",
                quarter_info={"accession_8k": "0001234567-89-000001"},
            )


def test_derive_mode_logic():
    assert A._derive_mode(None) == "live"
    assert A._derive_mode("2024-09-15T16:00:00+00:00") == "historical"
```

#### Stage 12 gate (standard COPY pattern)

#### Stage 12 commit
```bash
cd /home/faisal/em-builders-restructure
git add scripts/earnings/builders/adapters.py \
        scripts/earnings/builders/__init__.py \
        scripts/earnings/test_builders_adapters.py
git commit -m "refactor(builders): copy builder_adapters to adapters.py + canonicalize lazy imports + extend __init__ (commit 12/20)"
```

---

### Stage 13 — SHIM old `builder_adapters.py` + enable static AST test (1 commit)

#### Edit A — Replace `scripts/earnings/builder_adapters.py` with the module-only shim from §5.2.

#### Edit B — Extend `MODULE_PAIRS`

Include the 6 private adapter helpers explicitly. None are externally imported
TODAY (verified by grep), but the shim must preserve their identity for
forward-compat with future test/refactor callers. Cheap insurance that
locks in the contract now while the move is fresh.

```python
MODULE_PAIRS["builder_adapters"] = (
    "scripts.earnings.builders.adapters",
    [
        # Public adapter API (called by orchestrator + debug tools)
        "build_8k_packet", "build_guidance_history", "build_inter_quarter_context",
        "build_peer_earnings_snapshot", "build_macro_snapshot",
        "build_consensus", "build_prior_financials",
        # Private adapter helpers — re-exported via globals().update() shim.
        # Lock in identity so future code can rely on the contract.
        "_SuppressStdout", "_enrich_packet", "_write_enriched",
        "_ensure_dir", "_derive_mode", "_now_iso",
    ],
)
```

#### Edit C — Add static AST test `scripts/earnings/test_builders_static.py`

```python
"""Static AST verification — old shim files must contain NO real business logic.

This test is enabled in Stage 13 (after every shim has landed) and is a
permanent regression guard. If anyone re-introduces a `def` or `class` in a
shim file, this test fires immediately.
"""
from __future__ import annotations
import ast
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[2]

SHIM_FILES = [
    REPO / "scripts/earnings/builder_adapters.py",
    REPO / "scripts/earnings/build_consensus.py",
    REPO / "scripts/earnings/build_prior_financials.py",
    REPO / "scripts/earnings/macro_snapshot.py",
    REPO / "scripts/earnings/peer_earnings_snapshot.py",
    REPO / ".claude/skills/earnings-orchestrator/scripts/warmup_cache.py",
]

# CLI-capable shims must include `if __name__ == "__main__":`
CLI_CAPABLE = {
    REPO / "scripts/earnings/build_consensus.py",
    REPO / "scripts/earnings/build_prior_financials.py",
    REPO / "scripts/earnings/macro_snapshot.py",
    REPO / "scripts/earnings/peer_earnings_snapshot.py",
    REPO / ".claude/skills/earnings-orchestrator/scripts/warmup_cache.py",
}


@pytest.mark.parametrize("shim_path", SHIM_FILES)
def test_shim_has_no_function_def(shim_path):
    tree = ast.parse(shim_path.read_text())
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    assert not funcs, f"{shim_path} contains FunctionDef nodes: {[f.name for f in funcs]}"


@pytest.mark.parametrize("shim_path", SHIM_FILES)
def test_shim_has_no_class_def(shim_path):
    tree = ast.parse(shim_path.read_text())
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    assert not classes, f"{shim_path} contains ClassDef nodes: {[c.name for c in classes]}"


@pytest.mark.parametrize("shim_path", SHIM_FILES)
def test_shim_references_canonical_package(shim_path):
    text = shim_path.read_text()
    assert "scripts.earnings.builders" in text, (
        f"{shim_path} does not reference scripts.earnings.builders"
    )


@pytest.mark.parametrize("shim_path", sorted(CLI_CAPABLE))
def test_cli_shim_has_main_block(shim_path):
    text = shim_path.read_text()
    assert '__name__ == "__main__"' in text or "__name__ == '__main__'" in text, (
        f"{shim_path} is CLI-capable but missing __main__ block"
    )


@pytest.mark.parametrize("shim_path", SHIM_FILES)
def test_shim_all_excludes_underscore_names(shim_path):
    """`__all__` in every shim must EXCLUDE underscore-prefixed names so that
    `from <shim> import *` retains the same wildcard surface as the canonical
    module had before relocation.

    Underscore names are still bound to the shim's globals via `globals()[]`
    (so `from <shim> import _priv` still works) — they are just absent from
    `__all__`. This preserves the OLD `from <shim> import *` semantics: only
    public names, no private leakage.

    If this test fails, someone reverted the shim template to the simpler
    `__all__ = [n for n in dir(_impl) if not n.startswith("__")]` which would
    leak underscore names through `*`-import. The fix is in §5 shim templates.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        f"_shim_test_{shim_path.stem}", shim_path,
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    underscored = [n for n in mod.__all__ if n.startswith("_")]
    assert not underscored, (
        f"{shim_path} __all__ leaks underscore names: {underscored}. "
        f"Fix the shim template per §5 — the `__all__` line must filter on "
        f"`not _name.startswith('_')`, not `not _name.startswith('__')`."
    )
```

#### Stage 13 gate (standard) + extras
```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_imports.py scripts/earnings/test_builders_static.py -v
$PY scripts/earnings/test_adapter_validation.py --ticker FIVE
```

#### Stage 13 commit
```bash
cd /home/faisal/em-builders-restructure
git add scripts/earnings/builder_adapters.py \
        scripts/earnings/test_builders_imports.py \
        scripts/earnings/test_builders_static.py
git commit -m "refactor(builders): shim old builder_adapters + enable static AST test (commit 13/20)"
```

---

### Stage 14 — Update orchestrator + debug tools to canonical imports (1 commit)

#### Files changed
```text
scripts/earnings/earnings_orchestrator.py
scripts/earnings/render_section.py
scripts/earnings/compare_section.py
```

#### Edit A — `scripts/earnings/earnings_orchestrator.py`

OLD (lines 32-40):
```python
from builder_adapters import (
    build_8k_packet,
    build_guidance_history,
    build_inter_quarter_context,
    build_peer_earnings_snapshot,
    build_macro_snapshot,
    build_consensus,
    build_prior_financials,
)
```

NEW:
```python
from scripts.earnings.builders import (
    build_8k_packet,
    build_guidance_history,
    build_inter_quarter_context,
    build_peer_earnings_snapshot,
    build_macro_snapshot,
    build_consensus,
    build_prior_financials,
)
```

#### Edits B, C — `render_section.py` and `compare_section.py`

These files currently do only `sys.path.insert(0, str(Path(__file__).parent))`,
which adds ONLY `scripts/earnings/` to `sys.path`. For the new qualified
import `from scripts.earnings.builders import (...)` to resolve, the REPO ROOT
must also be on `sys.path` (so Python can find the top-level `scripts` package).
Therefore the path-setup block MUST be expanded BEFORE the canonical import.

**OLD (top of `render_section.py`, around lines 11-18):**
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from quarter_identity import resolve_quarter_info
from builder_adapters import (
    build_consensus, build_8k_packet, build_guidance_history,
    build_prior_financials, build_inter_quarter_context,
    build_peer_earnings_snapshot, build_macro_snapshot,
)
```

**NEW:**
```python
import sys
from pathlib import Path

# parents[2] = repo root; parents[1] = scripts/; parents[0] = scripts/earnings/
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))                          # for `scripts.earnings.builders` qualified imports
sys.path.insert(0, str(_PROJECT_ROOT / "scripts/earnings"))     # for bare `quarter_identity`, `earnings_orchestrator` etc.

from quarter_identity import resolve_quarter_info
from scripts.earnings.builders import (
    build_consensus, build_8k_packet, build_guidance_history,
    build_prior_financials, build_inter_quarter_context,
    build_peer_earnings_snapshot, build_macro_snapshot,
)
```

Apply the SAME path-setup change in `compare_section.py` (its old `sys.path.insert(0, str(Path(__file__).parent))` line is at line 21, with the import block at lines 24-28).

#### Files NOT updated (deliberate)

- **All `test_*.py` files** — they test the back-compat surface; keep on bare imports
- **`concept_fallback_discovery.py`** and **`q4_derivation.py`** — these are sidecars; keep on bare imports for now; updating them is a separate cleanup

#### Stage 14 gate (standard) + extras
```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
$PY -m py_compile scripts/earnings/earnings_orchestrator.py scripts/earnings/render_section.py scripts/earnings/compare_section.py
$PY scripts/earnings/earnings_orchestrator.py --test
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_renderer_*.py -q

# Step 1: py_compile catches SYNTAX errors only (it does NOT validate that
# imports resolve or that names exist at runtime). We CANNOT
# `importlib.import_module("render_section")` here because render_section.py
# and compare_section.py execute CLI logic at MODULE LEVEL (e.g.
# render_section.py:48 `if section == "all":` — top-level branch on parsed
# argv). Importing with no argv would crash on argv indexing.
$PY -m py_compile \
    scripts/earnings/render_section.py \
    scripts/earnings/compare_section.py
echo "render_section.py + compare_section.py syntax OK"

# Step 2: ast-verify the new import line is actually present in each file.
# This catches typos in the import path that py_compile would silently miss.
$PY -c "
import ast
for path in ('scripts/earnings/render_section.py', 'scripts/earnings/compare_section.py'):
    tree = ast.parse(open(path).read())
    found = any(
        isinstance(n, ast.ImportFrom)
        and n.module == 'scripts.earnings.builders'
        for n in ast.walk(tree)
    )
    assert found, f'{path}: scripts.earnings.builders import not found in AST'
print('ast import-line check OK')
"

# Step 3: actually exercise the canonical surface — proves
# scripts.earnings.builders package resolves AND exports the 7 functions.
# This is the runtime check py_compile alone cannot provide. Does NOT touch
# render_section/compare_section (they would crash on argv parsing).
PYTHONPATH=. $PY -c "
from scripts.earnings.builders import (
    build_8k_packet, build_guidance_history, build_inter_quarter_context,
    build_peer_earnings_snapshot, build_macro_snapshot,
    build_consensus, build_prior_financials,
)
print('canonical surface imports OK')
"
```

**Real-arg execution (only if Neo4j reachable — exercises the full import + body):**
```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
$PY scripts/earnings/render_section.py AVGO 0001730168-23-000093 header
$PY scripts/earnings/compare_section.py AVGO 0001730168-23-000093 guidance
```
The CLI run is the only smoke that proves the FULL render_section.py body
(including its argv parsing and downstream Neo4j calls) still works; the
3-step check above proves syntax + ast-line presence + canonical-surface
runtime resolution but not the file's full module body.

#### Stage 14 commit
```bash
cd /home/faisal/em-builders-restructure
git add scripts/earnings/earnings_orchestrator.py \
        scripts/earnings/render_section.py \
        scripts/earnings/compare_section.py
git commit -m "refactor(builders): migrate orchestrator + debug tools to canonical imports (commit 14/20)"
```

---

### Stage 15 — Promote identity test + AST static test as permanent regression guard (1 commit)

#### Goal
Promote tests added in earlier stages from "scaffold + per-stage additions" to "permanent regression guard" with a final completeness pass.

#### Edit — append to `test_builders_imports.py`

```python
def test_builders_package_public_surface():
    """The scripts.earnings.builders package exposes the 7 adapter functions."""
    import scripts.earnings.builders as pkg
    expected = {
        "build_8k_packet", "build_guidance_history", "build_inter_quarter_context",
        "build_peer_earnings_snapshot", "build_macro_snapshot",
        "build_consensus", "build_prior_financials",
    }
    for name in expected:
        assert hasattr(pkg, name), f"package surface missing {name}"
    assert set(pkg.__all__) >= expected


def test_package_root_re_exports_identity_with_adapters_submodule():
    """Stage 14 makes orchestrator do `from scripts.earnings.builders import (...)`,
    which resolves through scripts.earnings.builders/__init__.py — the package
    root. The package's __init__ does `from .adapters import (...)`, so the 7
    adapter functions must be the SAME objects when accessed via the package
    root vs the adapters submodule.

    If __init__.py ever switches to `import` (e.g. `from . import adapters` then
    `build_consensus = adapters.build_consensus`), that's still fine — but
    if anyone refactors __init__ to wrap or copy the functions, identity breaks
    here. This test catches that immediately.
    """
    import scripts.earnings.builders as pkg
    import scripts.earnings.builders.adapters as adapters_mod
    for name in ("build_8k_packet", "build_guidance_history",
                 "build_inter_quarter_context", "build_peer_earnings_snapshot",
                 "build_macro_snapshot", "build_consensus",
                 "build_prior_financials"):
        pkg_obj = getattr(pkg, name)
        adapter_obj = getattr(adapters_mod, name)
        assert pkg_obj is adapter_obj, (
            f"package root scripts.earnings.builders.{name} ({id(pkg_obj)}) "
            f"is NOT the same object as scripts.earnings.builders.adapters.{name} "
            f"({id(adapter_obj)}) — orchestrator's canonical import would "
            f"diverge from direct submodule access"
        )


def test_module_pairs_completeness():
    """MODULE_PAIRS must cover every public + private symbol from EXPECTED_SURFACE."""
    from test_builders_surface import EXPECTED_SURFACE
    covered = {
        (mod, sym)
        for mod, (_, syms) in MODULE_PAIRS.items()
        for sym in syms
    }
    missing = []
    for modname, spec in EXPECTED_SURFACE.items():
        for sym in spec["public"] + spec["private_exports"]:
            if (modname, sym) not in covered:
                missing.append(f"{modname}.{sym}")
    # main is checked by CLI smoke, not identity — exclude
    missing = [m for m in missing if not m.endswith(".main")]
    assert not missing, f"MODULE_PAIRS missing rows: {missing}"


def test_concurrent_imports_preserve_identity():
    """Smoke-test concurrent imports of old bare, old qualified, and new canonical
    paths. Python's import lock should make this safe by language guarantee, but
    the orchestrator's ThreadPoolExecutor spawns ALL 7 builders in parallel — if
    any builder's import has a side-effect that races with another, it would
    surface here.

    Strategy: 4 threads each import one of {old bare, old qualified, new
    canonical} for the same set of modules; after join, identity tests in
    MODULE_PAIRS must still hold.
    """
    import threading
    import importlib

    mods_to_import = [
        "build_consensus", "scripts.earnings.build_consensus",
        "scripts.earnings.builders.consensus",
        "build_prior_financials", "scripts.earnings.build_prior_financials",
        "scripts.earnings.builders.prior_financials",
        "warmup_cache", "scripts.earnings.builders.warmup_cache",
        "builder_adapters", "scripts.earnings.builder_adapters",
        "scripts.earnings.builders.adapters",
    ]
    errors: list[Exception] = []

    def _worker(name: str):
        try:
            importlib.import_module(name)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=_worker, args=(name,)) for name in mods_to_import]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert not errors, f"Concurrent imports raised: {errors}"

    # After concurrent imports, identity invariant must STILL hold.
    # Pick one representative symbol per builder and re-check.
    samples = [
        ("build_consensus", "scripts.earnings.builders.consensus", "build_consensus"),
        ("build_prior_financials", "scripts.earnings.builders.prior_financials", "_parse_value"),
        ("warmup_cache", "scripts.earnings.builders.warmup_cache", "build_8k_packet"),
        ("builder_adapters", "scripts.earnings.builders.adapters", "build_consensus"),
    ]
    for old_bare, new_qual, sym in samples:
        old_obj = getattr(importlib.import_module(old_bare), sym)
        new_obj = getattr(importlib.import_module(new_qual), sym)
        assert old_obj is new_obj, (
            f"IDENTITY BROKEN after concurrent imports: {old_bare}.{sym} != {new_qual}.{sym}"
        )
```

#### Stage 15 gate
```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_imports.py scripts/earnings/test_builders_static.py scripts/earnings/test_builders_surface.py -v
# expect: all parametrized rows + named tests green
```

#### Stage 15 commit
```bash
cd /home/faisal/em-builders-restructure
git add scripts/earnings/test_builders_imports.py
git commit -m "test(builders): finalize identity invariant + completeness guard (commit 15/20)"
```

---

### Stage 16 — README (MANDATORY, 1 commit)

#### Edit — `scripts/earnings/builders/README.md`

```markdown
# scripts/earnings/builders — canonical builder package

This subpackage was created on 2026-04-25 by relocating 6 builder files into
a single folder. See `.claude/plans/builders_restructure.md` for the
full move plan and TDD-driven safety invariants.

## Layout

| File | Responsibility |
|---|---|
| `_paths.py` | Centralized repo-root + sys.path discipline (the load-bearing helper) |
| `adapters.py` | Uniform adapter wrappers around the underlying builders |
| `consensus.py` | Consensus history (AV + Yahoo fallback) |
| `prior_financials.py` | Prior financial trends + revenue splits |
| `macro_snapshot.py` | Macro snapshot (indicators + Benzinga headlines) |
| `peer_earnings_snapshot.py` | Peer earnings snapshot |
| `warmup_cache.py` | 8K packet + guidance history + inter-quarter context |

## Shim contract

There is a permanent compatibility shim at every OLD path. **DO NOT delete:**

- `scripts/earnings/builder_adapters.py`
- `scripts/earnings/build_consensus.py`
- `scripts/earnings/build_prior_financials.py`
- `scripts/earnings/macro_snapshot.py`
- `scripts/earnings/peer_earnings_snapshot.py`
- `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py` (also the script-target for warmup_cache.sh)

Each shim does (matches the §5 templates — README and templates MUST stay in sync):
```python
from scripts.earnings.builders import <module> as _impl

# Step 1: bind ALL non-dunder names (public + private) into the shim's globals,
# so direct underscore imports work — `from <shim> import _parse_value` etc.
for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

# Step 2: __all__ is PUBLIC names only (no leading underscore), so
# `from <shim> import *` keeps the same wildcard surface as the original
# module (which had no __all__ and therefore defaulted to public-only).
__all__ = [_name for _name in dir(_impl) if not _name.startswith("_")]
del _name
```

This two-step pattern preserves direct-import identity for private helpers
(`_parse_value`, `_parse_dt_for_pit`, `classify_period`, `is_target_period`,
etc.) AND keeps the original `from <module> import *` semantic intact. The
simpler one-liner `__all__ = [n for n in dir(_impl) if not n.startswith("__")]`
would leak underscore names through `*`-imports — a silent behavior change.
The static AST test `test_shim_all_excludes_underscore_names` enforces this
permanently.

## Identity invariant

`scripts/earnings/test_builders_imports.py` enforces that every relocated symbol
resolves to the SAME function object via Python `is` from every import path. If
it fails, identity has been broken — revert and investigate.

## Static shim guard

`scripts/earnings/test_builders_static.py` asserts that old shim files contain
NO `FunctionDef` or `ClassDef` AST nodes after Stage 13. This is the permanent
guard against accidentally re-introducing logic into a shim file.

## Adding a new builder

1. Add the module to `builders/`.
2. If the underlying function should be exposed by `adapters.py`, add it there.
3. If callers should be able to import from `scripts.earnings.builders` directly,
   re-export in `__init__.py` and add to `__all__`.
4. Add a row to `EXPECTED_SURFACE` in `test_builders_surface.py`.
5. (No shim needed — the file lives in the canonical location from day one.)
```

#### Stage 16 commit
```bash
cd /home/faisal/em-builders-restructure
git add scripts/earnings/builders/README.md
git commit -m "docs(builders): document subpackage layout + shim contract (commit 20/20)"
```

---

## 11. Final State Verification (run inside the worktree, after all stages)

```bash
set -eo pipefail
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python

echo "=== File state ==="
echo "Builder modules in builders/ (expect 8 .py files: __init__, _paths, adapters, consensus, prior_financials, macro_snapshot, peer_earnings_snapshot, warmup_cache + 1 README.md):"
ls scripts/earnings/builders/
echo ""

echo "Shim files at OLD paths (expect 6 — must be tiny, no def/class):"
for f in scripts/earnings/builder_adapters.py \
         scripts/earnings/build_consensus.py \
         scripts/earnings/build_prior_financials.py \
         scripts/earnings/macro_snapshot.py \
         scripts/earnings/peer_earnings_snapshot.py \
         .claude/skills/earnings-orchestrator/scripts/warmup_cache.py; do
  if grep -q "scripts.earnings.builders" "$f"; then
    lines=$(wc -l < "$f")
    echo "  $f: shim OK ($lines lines)"
  else
    echo "  $f: SHIM CONTRACT BROKEN"; exit 1
  fi
done
echo ""

echo "=== Static guard: no def build_ or class in shim files ==="
! rg -n "^def build_|^class " scripts/earnings/builder_adapters.py scripts/earnings/build_consensus.py scripts/earnings/build_prior_financials.py scripts/earnings/macro_snapshot.py scripts/earnings/peer_earnings_snapshot.py .claude/skills/earnings-orchestrator/scripts/warmup_cache.py && echo "PASS: no real defs in shims"

echo "=== Static guard: real defs ARE in canonical package ==="
rg -n "^def build_" scripts/earnings/builders/

echo ""
echo "=== Path math clean in canonical modules ==="
# Regex matches only parents[2] (the wrong-after-move index for builders/X.py)
# and the hardcoded production path. parents[3] is INTENTIONAL in _paths.py
# (REPO_ROOT = Path(__file__).resolve().parents[3]) and must NOT trigger this
# guard, which is why the regex is parents[2]-specific rather than the broad
# `Path(__file__).resolve().parents` alternative.
#
# EXCLUDE _paths.py from the scan: its DOCSTRING intentionally references the
# string "parents[2]" to explain WHY this module exists (old files used that
# expression and broke at the deeper subpackage location). The string in the
# docstring is documentation, not code, and would false-trigger the guard.
! rg -n "parents\[2\]|/home/faisal/EventMarketDB" scripts/earnings/builders/ --glob '!_paths.py' && echo "PASS: no stale path math"

echo ""
echo "=== Compile checks ==="
$PY -m py_compile \
  scripts/earnings/builders/*.py \
  scripts/earnings/builder_adapters.py \
  scripts/earnings/build_consensus.py \
  scripts/earnings/build_prior_financials.py \
  scripts/earnings/macro_snapshot.py \
  scripts/earnings/peer_earnings_snapshot.py \
  .claude/skills/earnings-orchestrator/scripts/warmup_cache.py \
  scripts/earnings/earnings_orchestrator.py \
  scripts/earnings/render_section.py \
  scripts/earnings/compare_section.py

echo ""
echo "=== Test matrix ==="
PYTHONPATH=. $PY -m pytest scripts/earnings/test_builders_paths.py -v
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_imports.py -v
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_static.py -v
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_surface.py -v
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_*.py -v -m "not live"
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_renderer_*.py -q
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_av_client.py scripts/earnings/test_q4_derivation.py scripts/earnings/test_xbrl_exact_splits.py -q

echo ""
echo "=== Orchestrator self-test ==="
PYTHONPATH=scripts/earnings $PY scripts/earnings/earnings_orchestrator.py --test
# expect: 9 passed, 0 failed out of 9

echo ""
echo "=== CLI smoke (every old + new path) ==="
$PY .claude/skills/earnings-orchestrator/scripts/warmup_cache.py --test
$PY -m scripts.earnings.builders.warmup_cache --test
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh --test

# Old + new packets — normalized comparison
$PY scripts/earnings/peer_earnings_snapshot.py AVGO --pit 2023-12-07T16:18:51-05:00 --out-path /tmp/old_peers.json
$PY -m scripts.earnings.builders.peer_earnings_snapshot AVGO --pit 2023-12-07T16:18:51-05:00 --out-path /tmp/new_peers.json
diff <(jq -S 'del(.assembled_at) | .gaps |= sort_by(tostring)' /tmp/old_peers.json) \
     <(jq -S 'del(.assembled_at) | .gaps |= sort_by(tostring)' /tmp/new_peers.json) && echo "PASS: peer packets match (normalized)"

echo ""
echo "=== Consumer-import smoke ==="
PYTHONPATH=scripts/earnings $PY -c "
import earnings_orchestrator   # IMPORTED — exercises full module body
import concept_fallback_discovery  # IMPORTED — exercises full module body
import q4_derivation           # IMPORTED — exercises full module body
import importlib.util
# render_section.py and compare_section.py do CLI argv parsing at MODULE LEVEL
# (render_section.py:48 `if section == \"all\":`), so importing them with no
# argv would crash. We only confirm the module is FINDABLE on sys.path here;
# their actual import is exercised separately by py_compile + the §14 ast
# import-line check + the optional Neo4j-reachable CLI run.
for mod in ('render_section', 'compare_section'):
    assert importlib.util.find_spec(mod) is not None, mod
print('orchestrator/concept_fallback/q4_derivation: imported OK')
print('render_section/compare_section: spec found (full import exercised by §14 CLI run)')
"

echo ""
echo "=== Commit log on builders-restructure ==="
git log --oneline pre-builders-restructure-baseline..HEAD
# expect: 20 commits
```

### MANDATORY live integration before merge

**Mocked tests are insufficient proof for a 6,602-line relocation that touches Neo4j, AV, Polygon, Yahoo, and Benzinga.** The two scripts below MUST pass on at least one ticker before merge:

```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
$PY scripts/earnings/test_adapter_validation.py --ticker FIVE
$PY scripts/earnings/test_builder_validation.py --ticker FIVE
```

Rules:
- **If Neo4j is reachable:** both scripts MUST pass before merge. No exceptions.
- **If Neo4j is unreachable:** STOP and ask the user. Do NOT merge on mocks alone.
- **Alpha Vantage `--allow-av`** remains opt-in (quota is exhausted externally; one missed live AV check should not block).

```bash
# Optional AV gate — only if quota is available
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
$PY scripts/earnings/test_adapter_validation.py --ticker FIVE --allow-av
```

---

## 12. Production Quiescence + ff-Merge

Same pattern as the renderer move (proven on 2026-04-25, commit `6bb2c6d`).

### Pre-merge quiescence (run from MAIN repo)

```bash
cd /home/faisal/EventMarketDB

echo "=== Redis queue depth (extract:pipeline) ==="
kubectl -n infrastructure exec deploy/redis -- redis-cli LLEN extract:pipeline
# expect: 0

echo "=== extraction-worker pod state ==="
kubectl -n processing get pods -l app=extraction-worker --no-headers
# expect: NO output

echo "=== KEDA scaler state ==="
kubectl -n processing get scaledobject extraction-worker-scaler -o jsonpath='{.metadata.annotations.autoscaling\.keda\.sh/paused-replicas}{" "}{.spec.minReplicaCount}{" "}{.spec.maxReplicaCount}{"\n"}'
```

If queue is non-empty OR pods running:
- **Either** wait for natural drain
- **Or** pause KEDA via supported annotation:
  ```bash
  kubectl -n processing annotate scaledobject extraction-worker-scaler \
      autoscaling.keda.sh/paused-replicas="0" --overwrite
  ```
  (Unpause after merge by removing the annotation: same command with trailing `-`.)

### ff-merge

```bash
cd /home/faisal/EventMarketDB
PY=/home/faisal/EventMarketDB/venv/bin/python
git checkout main
git pull --ff-only origin main

# CRITICAL: tag main HEAD BEFORE the merge so rollback can revert all 20
# builders commits. After `git merge --ff-only` there is NO merge commit
# (HEAD just fast-forwards), so `git revert -m 1 <merge>` does NOT work.
# The tag-based rollback below covers the entire commit range.
git tag pre-builders-main-before-merge HEAD

git merge --ff-only builders-restructure
echo "main HEAD: $(git rev-parse HEAD | head -c 12)"

# Re-gate on main
PYTHONPATH=. $PY -m pytest scripts/earnings/test_builders_paths.py -q
PYTHONPATH=scripts/earnings $PY -m pytest scripts/earnings/test_builders_*.py scripts/earnings/test_renderer_*.py -q -m "not live"
PYTHONPATH=scripts/earnings $PY scripts/earnings/earnings_orchestrator.py --test
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh --test

# Confirm production state still clean
kubectl -n processing get pods -l app=extraction-worker --no-headers
```

If merge is NOT fast-forwardable, abort:
```bash
cd /home/faisal/em-builders-restructure
git merge --abort
git tag -d pre-builders-main-before-merge
# Re-base builders-restructure on main inside the worktree, re-run all gates, retry.
```

### Post-merge cleanup (only after a successful merge AND post-merge re-gate)

```bash
cd /home/faisal/EventMarketDB
git worktree remove /home/faisal/em-builders-restructure
git branch -d builders-restructure
git push origin main   # only with explicit user approval
# Optional cleanup (the tag was a safety net; keep for ~24h before deleting):
# git tag -d pre-builders-main-before-merge
# git push origin :refs/tags/pre-builders-main-before-merge   # only if previously pushed
```

### Rollback (if anything fails post-merge)

`git merge --ff-only` does NOT create a merge commit, so there is no merge commit
to revert with `-m 1`. Use the tag-based revert that covers the full 20-commit
range that landed during the fast-forward:

```bash
cd /home/faisal/EventMarketDB
# Reverts every commit between the tag and HEAD with one inverse commit each.
# History stays linear and bisectable; no force-push needed.
git revert --no-edit pre-builders-main-before-merge..HEAD
git push origin main
```

KEDA's next scale-up picks up the reverted code on the same hostPath. Recovery time ≈ 5 min.

---

## 13. What We Are Explicitly NOT Doing

1. **Not renaming any function, class, or constant** inside the moved files
2. **Not editing any test file's import style** — tests stay on bare imports (regression coverage of shim layer)
3. **Not removing any old top-level file** — every shim is permanent
4. **Not modifying `warmup_cache.sh`** — behavior preserved purely via the shim's `__main__` delegation
5. **Not splitting `warmup_cache.py`** internally into eightk/guidance/inter_quarter modules in this PR
6. **Not making the `builders/` package self-sufficient as a top-level callable** — orchestrator remains entry point
7. **Not migrating sidecars** (`xbrl_exact_splits.py`, `q4_derivation.py`, `concept_fallback_discovery.py`, `fye_month.py`, `quarter_identity.py`, `av_client.py`, `get_*` data subagents) — those are separate refactors
8. **Not consolidating the two `_parse_dt_for_pit` functions** — same name, different implementations is intentional
9. **Not touching K8s manifests or hostPath** — deploy contract untouched
10. **Not running `test_builder_validation.py` / `test_adapter_validation.py` in per-stage gates** — they hit live external services, are not idempotent. CLI smoke + orchestrator `--test` are sufficient
11. **Not changing schemas, packet contents, default output paths, retry behavior, source policy, or live/PIT semantics**
12. **Not editing `.md` files, skill instructions, or string references** that mention old paths (e.g. `from build_consensus import ...`, `bash warmup_cache.sh ...`). The shims preserve those paths INTENTIONALLY — touching the docs creates pointless review surface and risks drift. Only update the README created in Stage 16 and any narrow path note required to avoid future confusion.
13. **Not changing subprocess invocation in `macro_snapshot.py`'s `pit_fetch.py` call.** The current `subprocess.run([...])` (no `env=`) inherits the parent's environment. Adding explicit env-tightening is hardening for hypothetical future invocation contexts but introduces a behavior change with unverified blast radius. The renderer-move precedent made zero subprocess changes; we follow that. If hardening is desired, do it as a separate PR with mandatory live integration verification.

---

## 14. Edge Cases & Gotchas

### 14.1 `test_fmt_guards.py` crashes pytest collection
Pre-existing repo bug — calls `sys.exit(1)` at module top. Per-stage gates use targeted globs (`test_renderer_*.py`, `test_builders_*.py`) — already avoids this.

### 14.2 Line numbers in this plan are illustrative
Edits should use semantic `old_string`/`new_string` matching, not literal line numbers.

### 14.3 The `_classifier` singleton (build_consensus)
After Stage 7, mutable module-level binding. No external caller imports `_classifier` directly (verified by grep). Internal callers all go through `_get_classifier()` reading `global _classifier` from inside the canonical module. Stage 7 identity test guards against split.

### 14.4 `_parse_dt_for_pit` shadowing
Two distinct functions in `warmup_cache` and `peer_earnings_snapshot`. Stage 11 disambiguation guard asserts they remain distinct objects after the move.

### 14.5 `warmup_cache.sh` script-target dependency
The shell wrapper does `exec python3 "$SCRIPT_DIR/warmup_cache.py" "$@"`. After Stage 11, `$SCRIPT_DIR/warmup_cache.py` is the SHIM file (delegates to canonical via `__main__`). End-user-visible behavior unchanged.

### 14.6 `globals().update()` shim mechanism
This pattern captures EVERY non-dunder name from the canonical module — public AND private. No need to enumerate underscore names manually. Survives `rg "def build_"` static check (no `def`/`class` nodes in shim). The renderer extraction's `from X import *` + explicit `from X import (_priv1, _priv2)` is functionally equivalent but more brittle.

### 14.7 `_paths.py` precedence order
SKILL_SCRIPTS_DIR > EARNINGS_DIR > SCRIPTS_DIR > REPO_ROOT (highest precedence first in sys.path). Matches current `builder_adapters.py` behavior. Do not change without separate import-shadowing audit.

### 14.8 `scripts.earnings` is a namespace package
No `scripts/__init__.py` or `scripts/earnings/__init__.py`. `scripts.earnings.X` resolves via `_NamespacePath`. We add a regular `__init__.py` for `builders/` only. **Do not add `__init__.py` to scripts/ or scripts/earnings/** in this PR — could change import behavior.

### 14.9 If a stage gate fails
- Fix in place if cause is obvious (typo, missed Edit). Re-run gate. Do NOT commit half-broken stage.
- If non-obvious, `git revert HEAD` to undo (keeps bisect property). Diagnose from known-good state.
- NEVER amend or `git reset --hard`.

### 14.10 If venv is missing required deps
`ModuleNotFoundError: No module named 'dotenv'` — STOP. Do not fall back to system python. Verify `ls /home/faisal/EventMarketDB/venv/bin/python`.

### 14.11 Worktree path/branch already exists
Pre-flight §9.2 catches this. Do NOT proceed past FATAL message — clean up first per the printed instructions.

### 14.12 Extraction-worker scales up mid-execution
Pod loads from disk on boot. Worktree is isolated from hostPath mount during stages. Risk window is the §12 ff-merge — addressed by quiescence check.

### 14.13 If you need to abort mid-execution

**Before §12 merge:** `git worktree remove --force /home/faisal/em-builders-restructure && git branch -D builders-restructure`. Main untouched.

**After §12 merge (whether or not pushed):** the `--ff-only` merge created NO merge commit, so reverting with `-m 1 <merge>` is NOT applicable. Use the tag-based revert documented in §12 — `git revert --no-edit pre-builders-main-before-merge..HEAD` — which works equally before and after push.

Do NOT use `git reset --hard` here. The fast-forward landed 20 commits at once; a `reset --hard HEAD~1` would only undo ONE of them, leaving the working tree in a hybrid mid-stage state.

---

## 15. Aggregate Risk Assessment

| Stage | Files touched | Identity preserved? | Renderer green? | Reversibility |
|---|---|---|---|---|
| 0 (TDD foundation) | +3 test files + tag | n/a (no moves) | yes | revert HEAD~3..HEAD |
| 1 (`_paths.py`) | +3 files | n/a | yes | git revert HEAD |
| 2 (COPY peer) | +1 canonical + 1 test | n/a (additive) | yes | git revert HEAD |
| 3 (SHIM peer) | 1 modified | yes (4 symbols) | yes | git revert HEAD |
| 4 (COPY macro) | +2 files | n/a | yes | git revert HEAD |
| 5 (SHIM macro) | 1 modified | yes (3 symbols) | yes | git revert HEAD |
| 6 (COPY consensus) | +2 files | n/a | yes | git revert HEAD |
| 7 (SHIM consensus + singleton) | 1 modified + test | yes (4 symbols + singleton) | yes | git revert HEAD |
| 8 (COPY prior_financials) | +2 files | n/a | yes | git revert HEAD |
| 9 (SHIM prior_financials + xbrl) | 1 modified + test | yes (7 symbols + xbrl) | yes | git revert HEAD |
| 10 (COPY warmup) | +2 files | n/a | yes | git revert HEAD |
| 11 (SHIM warmup + shadow) | 1 modified + test | yes (12 symbols + shadow) | yes | git revert HEAD |
| 12 (COPY adapters + canonicalize lazy) | +3 files | n/a | yes | git revert HEAD |
| 13 (SHIM adapters + AST static) | 1 modified + test | yes (7 symbols + AST guard) | yes | git revert HEAD |
| 14 (consumer canonical imports) | 3 modified | yes (renames only) | yes | git revert HEAD |
| 15 (permanent guards) | 1 modified | yes (already true) | yes | git revert HEAD |
| 16 (README) | +1 file | n/a | yes | git revert HEAD |

**Aggregate residual risk: practically zero** because:
- Path math centralized in `_paths.py` — no risk of missed `parents[2]` site
- Function bodies byte-identical across every stage (only path setup changes)
- 4-path identity preserved across every move; explicitly asserted by `MODULE_PAIRS` parametrize
- COPY-then-SHIM 2-step per file: production never sees "moved-but-no-shim" state
- Shim mechanism (loop binding non-dunder names into shim globals + public-only `__all__`) captures all non-dunder names for direct imports while preserving `from X import *` wildcard semantics — no enumeration risk and no underscore-leak risk
- Static AST test enforces "shim files have no business logic" permanently
- Per-builder mocked unit tests give deterministic verification independent of live services
- Three risk-specific identity guards: singleton (build_consensus._classifier), shadow (`_parse_dt_for_pit`), lazy import (xbrl_exact_splits)
- Renderer suite (167 tests) and orchestrator `--test` (9/9) baseline-green at every stage
- Worktree isolation: production NEVER sees stages 0–15 intermediate states
- ff-merge gated on documented quiescence

---

## 16. Done Criteria

- [ ] Pre-flight: worktree `/home/faisal/em-builders-restructure` exists on `builders-restructure` (off main)
- [ ] Renderer baseline + orchestrator `--test` 9/9 + `warmup_cache.sh --test` all green
- [ ] Stage 0 (4 commits): baseline tag + packet snapshots + 3 test files
- [ ] Stage 1 (1 commit): `_paths.py` + 9 path-helper tests pass
- [ ] Stage 2 (1 commit): canonical `peer_earnings_snapshot.py` copied; mocked tests pass
- [ ] Stage 3 (1 commit): old `peer_earnings_snapshot.py` shimmed; identity verified
- [ ] Stage 4 (1 commit): canonical `macro_snapshot.py` copied; mocked tests pass
- [ ] Stage 5 (1 commit): old `macro_snapshot.py` shimmed; identity verified
- [ ] Stage 6 (1 commit): canonical `consensus.py` copied; mocked tests pass
- [ ] Stage 7 (1 commit): old `build_consensus.py` shimmed; classifier-singleton guard green
- [ ] Stage 8 (1 commit): canonical `prior_financials.py` copied; mocked tests pass
- [ ] Stage 9 (1 commit): old `build_prior_financials.py` shimmed; xbrl lazy-import guard green
- [ ] Stage 10 (1 commit): canonical `warmup_cache.py` copied; module `--test` green
- [ ] Stage 11 (1 commit): old `.claude/.../warmup_cache.py` shimmed; cross-module shadow guard green; `warmup_cache.sh --test` works
- [ ] Stage 12 (1 commit): canonical `adapters.py` copied with canonical lazy imports; `__init__` extended
- [ ] Stage 13 (1 commit): old `builder_adapters.py` shimmed; AST static test enabled
- [ ] Stage 14 (1 commit): orchestrator + render_section + compare_section migrated to canonical imports
- [ ] Stage 15 (1 commit): permanent identity test + completeness guard
- [ ] Stage 16 (1 commit, MANDATORY): README at `scripts/earnings/builders/README.md`
- [ ] Final verification (§11) all green inside the worktree
- [ ] **Mandatory live integration:** `test_adapter_validation.py --ticker FIVE` and `test_builder_validation.py --ticker FIVE` BOTH pass (or Neo4j unreachable → STOP and ask user)
- [ ] `git log --oneline pre-builders-restructure-baseline..HEAD` shows exactly **20 commits**
- [ ] `pre-builders-main-before-merge` tag created on main BEFORE the ff-merge
- [ ] FF-merge into main during quiescence; re-run gate on main; identical results
- [ ] Cleanup: worktree removed, `builders-restructure` branch deleted
- [ ] Optionally push to origin: `git push origin main` (with explicit approval)

---

## 17. Review Pass Checklist

The implementing bot must perform these review passes before final merge.

### Review Pass 0 — Test Code Itself

**Test code can have bugs that pass-without-proving.** A passing test that
patches the wrong target or asserts on a wrong shape silently lets regressions
through. Three real examples were caught in this plan's review cycle:

  1. `_fetch_all_av` mock returned a dict, but the real function returns a tuple.
  2. `_yahoo_daily`/`_yahoo_minute` mocks returned scalars, but real functions return list[dict] of bars.
  3. `patch.object(bpf, "get_manager")` failed silently — `get_manager` is imported LOCALLY inside the function, not at module level.

**After Stage 0.2 + 0.3 + 0.4 land, MANUALLY code-review every new test file.**
Don't just run `pytest` and trust green. For each new test file, audit:

- **Patch targets:** does `patch.object(M, "func")` actually find an attribute on `M`,
  or is `func` imported lazily inside another function? Use `dir(M)` to verify.
- **Mock return shapes:** does the mock return value match the REAL function's
  signature (tuple vs dict, list vs scalar, optional vs required keys)?
  Cross-check with `inspect.signature()` and the real function's source.
- **Over-broad asserts:** does `assert "schema_version" in packet` actually
  prove anything, or would it pass for any dict with that key?
- **Live-service leaks:** does any code path inside the test still hit Neo4j /
  AV / Polygon / Yahoo / Benzinga? Add `patch()` for each.

This review pass exists because the cost of a wrong test is silent regression;
the cost of 30 minutes of code review is one tea break.

### Review Pass 1 — Import Surface
```bash
# Audit must run against the worktree branch state, NOT main. Without the cd
# the rg would scan whichever cwd the bot happens to be in.
cd /home/faisal/em-builders-restructure
rg -n "from (build_consensus|build_prior_financials|macro_snapshot|peer_earnings_snapshot|builder_adapters|warmup_cache)|import (build_consensus|build_prior_financials|macro_snapshot|peer_earnings_snapshot|builder_adapters|warmup_cache)" scripts .claude docs -g '*.py' -g '*.md' -g '*.sh'
```
Expected: old imports may remain in tests/docs/sidecars; main runtime consumers use `scripts.earnings.builders` after Stage 14; every old import still works through shims.

### Review Pass 2 — CLI Surface
```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
$PY scripts/earnings/peer_earnings_snapshot.py AVGO --pit 2023-12-07T16:18:51-05:00 --out-path /tmp/old_peers.json
$PY -m scripts.earnings.builders.peer_earnings_snapshot AVGO --pit 2023-12-07T16:18:51-05:00 --out-path /tmp/new_peers.json
$PY .claude/skills/earnings-orchestrator/scripts/warmup_cache.py --test
$PY -m scripts.earnings.builders.warmup_cache --test
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh --test
```

### Review Pass 3 — Path Safety
```bash
cd /home/faisal/em-builders-restructure
PY=/home/faisal/EventMarketDB/venv/bin/python
PYTHONPATH=. $PY -c "
from scripts.earnings.builders import _paths, macro_snapshot
print('REPO_ROOT     =', _paths.REPO_ROOT)
print('EARNINGS_DIR  =', _paths.EARNINGS_DIR)
print('SKILL_SCRIPTS =', _paths.SKILL_SCRIPTS_DIR)
print('PIT_FETCH     =', macro_snapshot.PIT_FETCH)
"
```
Expected (in worktree):
- REPO_ROOT = `/home/faisal/em-builders-restructure`
- EARNINGS_DIR = `/home/faisal/em-builders-restructure/scripts/earnings`
- SKILL_SCRIPTS = `/home/faisal/em-builders-restructure/.claude/skills/earnings-orchestrator/scripts`
- PIT_FETCH ends with `pit_fetch.py` and exists

### Review Pass 4 — Behavioral Equivalence
Compare normalized old vs new outputs for at least:
- `prior_financials` on `CHRW 2024-12-31`
- `peer_earnings_snapshot` on `AVGO 2023-12-07T16:18:51-05:00`
- `macro_snapshot` on `AVGO 2023-12-07T16:18:51-05:00`
- `warmup_cache --test`

Normalize: strip `assembled_at`, sort `gaps[]` by `(type, reason, str(gap))`.

### Review Pass 5 — Static No-Duplication
```bash
# Audit must run against the worktree branch state, NOT main, so that the
# shim files being scanned are the post-merge versions (otherwise the rg on
# main would still show the pre-relocation `def build_*` lines and false-fail).
cd /home/faisal/em-builders-restructure
rg -n "^def build_|^class " scripts/earnings/builder_adapters.py scripts/earnings/build_consensus.py scripts/earnings/build_prior_financials.py scripts/earnings/macro_snapshot.py scripts/earnings/peer_earnings_snapshot.py .claude/skills/earnings-orchestrator/scripts/warmup_cache.py
# expect: no output
rg -n "^def build_" scripts/earnings/builders
# expect: canonical defs found
```

### Review Pass 6 — Production Safety
- No extraction queue backlog (`LLEN extract:pipeline = 0`)
- No running extraction-worker pods
- Branch is fast-forwardable
- Final `git diff --stat main..builders-restructure` only includes planned files

---

## 18. Explicit Non-Regression Guarantees

This plan preserves behavior by construction:

1. Old imports keep working because old modules remain (as shims).
2. Old CLIs keep working because shim files have `if __name__ == "__main__":` blocks.
3. Function identity preserved after each shim swap because shims re-export exact objects via `globals().update()`.
4. Canonical code is copied first and used only after tests prove it imports and behaves equivalently.
5. Path changes centralized in `_paths.py`, not hand-edited differently in every file.
6. No schema fields are changed.
7. No default output paths are changed.
8. No live/PIT semantics are changed.
9. No retries/source policies are changed.
10. No old public or private helper path is removed.
11. `globals().update()` shim mechanism captures EVERY non-dunder name automatically, eliminating the risk of missing a private re-export.
12. Static AST test (`test_builders_static.py`) makes "shim is shim-only" a permanent invariant.
13. Path-helper tests (`test_builders_paths.py`) lock in `_paths.py` semantics including idempotence, deduplication, and precedence order.
14. Per-builder mocked unit tests (`test_builders_consensus.py`, etc.) verify each builder's behavior deterministically without live services.

Literal 0% regression risk is impossible for a 6,602-line relocation touching live-service code. **Practically near-zero risk** is achievable if and only if:

- The implementation follows the stage order
- Each stage is independently tested before proceeding
- Old paths remain permanent shims
- Final merge happens only while extraction workers are quiescent

---

**End of plan.**
