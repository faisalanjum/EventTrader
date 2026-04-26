#!/usr/bin/env python3
"""Compatibility shim. Canonical implementation lives in scripts.earnings.builders.warmup_cache.

This file ALSO serves as the script target for warmup_cache.sh — the shell
wrapper does `exec python3 "$SCRIPT_DIR/warmup_cache.py" "$@"`, so removing
this file would break agent calls. The shim's __main__ block REPLICATES the
canonical module's pre-main() dispatch (--test → _run_v2_regression_tests),
which is NOT inside main() itself.

DO NOT add logic here. All behavior lives in the canonical module.

Identity contract: every symbol re-exported by this shim MUST be the SAME
object (Python `is`) as the canonical-module symbol. The two-step mechanism
below guarantees this for ALL non-dunder names (public + private):

1. Loop binds every non-dunder name into shim globals — `from <shim> import _priv`
   resolves with byte-identical identity to the canonical module's `_priv`.
2. `__all__` is PUBLIC names only (no leading underscore) so that
   `from <shim> import *` keeps the same wildcard surface as the original
   module (which had no __all__ and therefore defaulted to public-only).

Special concerns for warmup_cache (most novel shim in this migration):
  - parents[4] for repo root (file lives 4 dirs deep under repo)
  - `--test` dispatched BEFORE `main()` — original bottom block did:
        if sys.argv[1] == '--test': sys.exit(0 if _run_v2_regression_tests() else 1)
        main()
    so the shim's __main__ must replicate this. _impl.main() alone would NOT
    handle --test correctly because main() does not know about --test.
  - `_parse_dt_for_pit` is a name shared with peer_earnings_snapshot but a
    DIFFERENT function. The shadow-guard test in test_builders_imports.py
    asserts they remain distinct objects.
"""
from __future__ import annotations

import sys
from pathlib import Path

# parents[4] = repo root from <repo>/.claude/skills/earnings-orchestrator/scripts/<this>.py
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.earnings.builders import warmup_cache as _impl

# Step 1: bind ALL non-dunder names (public + private) into shim globals.
for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

# Step 2: __all__ is public-only — preserves `from <shim> import *` semantic.
__all__ = [_name for _name in dir(_impl) if not _name.startswith("_")]
del _name

# CLI delegation — keep `python3 .../warmup_cache.py` AND `bash warmup_cache.sh`
# working. CRITICAL: replicate the OLD __main__ pre-dispatch — `--test` was
# handled OUTSIDE main() in the original, so plain `_impl.main()` would
# silently break `python warmup_cache.py --test` and `bash warmup_cache.sh --test`.
# _run_v2_regression_tests() returns a bool (verified: `return failed == 0`),
# so sys.exit() with the inverted truth value preserves the old exit-code
# semantic exactly.
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        sys.exit(0 if _impl._run_v2_regression_tests() else 1)
    _impl.main()
