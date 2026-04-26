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

# Step 3: SINGLETON-SHIM FIX (Stage 7.1).
# Mutable module-level globals (e.g. lazy singletons like _classifier) are
# captured by Step 1's eager-copy at SHIM-IMPORT time. When the canonical
# module's `global _classifier` mutates the cell later, the shim's snapshot
# stays stale (None). Function calls via _get_classifier() are identity-safe
# (the function itself reads canonical's `global _classifier`), but DIRECT
# attribute access (`build_consensus._classifier`) sees the stale snapshot.
#
# Fix: delete known mutable globals from the shim's __dict__, then install
# a PEP 562 module __getattr__ that forwards to canonical for any name
# missing from shim's __dict__. The forward fires for both `module.X` and
# `from module import X` lookups (PEP 562). This makes mutable accesses
# always reflect canonical's current state.
#
# Catalog of known mutable module-level globals in scripts.earnings.builders.consensus:
#   - _classifier  (lazy MarketSessionClassifier singleton; mutated by _get_classifier)
_MUTABLE_GLOBALS = ("_classifier",)
for _g in _MUTABLE_GLOBALS:
    if _g in globals():
        del globals()[_g]
del _g


def __getattr__(name):
    """PEP 562 module __getattr__ — forwards to canonical _impl for any name
    not in shim's __dict__. Serves both `<shim>.X` and `from <shim> import X`.
    Required for mutable-global forwarding (see Step 3 comment above)."""
    return getattr(_impl, name)


def __dir__():
    """PEP 562 module __dir__ — returns the union of shim's local names AND
    canonical _impl's names. Without this, dir() introspection would not list
    attributes served by the __getattr__ forward (e.g. deleted mutable globals
    like _classifier), contradicting hasattr() and diverging from canonical's
    introspection surface. Stage 7.2 fix."""
    return sorted(set(globals()) | set(dir(_impl)))


# CLI delegation — keep `python3 scripts/earnings/build_consensus.py ...` working.
if __name__ == "__main__":
    _impl.main()
