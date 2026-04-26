#!/usr/bin/env python3
"""Compatibility shim. Canonical implementation lives in scripts.earnings.builders.consensus.

This file exists ONLY to satisfy bare-name imports
    from build_consensus import X
that work because callers do `sys.path.insert(0, scripts/earnings)`.

DO NOT add logic here. All behavior lives in the canonical module.

Identity contract: every symbol re-exported by this shim MUST be the SAME
object (Python `is`) as the canonical-module symbol. The two-step mechanism
below guarantees this for ALL non-dunder names (public + private):

1. Loop binds every non-dunder name into shim globals — `from <shim> import _priv`
   resolves with byte-identical identity to the canonical module's `_priv`.
2. `__all__` is PUBLIC names only (no leading underscore) so that
   `from <shim> import *` keeps the same wildcard surface as the original
   module (which had no __all__ and therefore defaulted to public-only).

NOTE: build_consensus has a module-level mutable global `_classifier` (lazy
singleton initialized by `_get_classifier()`). The Stage 7 identity test
test_classifier_singleton_across_paths verifies that ALL import paths
dispatch to the canonical `_get_classifier()` and return the SAME singleton
object — preventing the singleton from splitting across module objects.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.earnings.builders import consensus as _impl

# Step 1: bind ALL non-dunder names (public + private) into shim globals.
for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

# Step 2: __all__ is public-only — preserves `from <shim> import *` semantic.
__all__ = [_name for _name in dir(_impl) if not _name.startswith("_")]
del _name

# CLI delegation — keep `python3 scripts/earnings/build_consensus.py ...` working.
if __name__ == "__main__":
    _impl.main()
