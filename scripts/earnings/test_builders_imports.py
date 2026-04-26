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
#   skill-scripts > earnings-local > scripts/ > repo root
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
MODULE_PAIRS: dict[str, tuple[str, list[str]]] = {
    "peer_earnings_snapshot": (
        "scripts.earnings.builders.peer_earnings_snapshot",
        ["build_peer_earnings_snapshot", "render_text", "main", "_parse_dt_for_pit"],
    ),
    "macro_snapshot": (
        "scripts.earnings.builders.macro_snapshot",
        ["build_macro_snapshot", "render_text", "main"],
    ),
    "build_consensus": (
        "scripts.earnings.builders.consensus",
        ["build_consensus", "main", "_parse_iso", "_normalize_session"],
    ),
    "build_prior_financials": (
        "scripts.earnings.builders.prior_financials",
        ["build_prior_financials", "classify_period", "is_target_period",
         "dedupe_facts", "main", "_parse_value"],
    ),
}


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


def test_classifier_singleton_across_paths():
    """build_consensus._classifier must be one cell across all import paths.
    If this fails, the module loaded twice and the lazy singleton split.

    Three import paths exist for build_consensus after Stage 7:
      1. `import build_consensus`                     (bare, via OLD-path shim)
      2. `import scripts.earnings.build_consensus`    (qualified, via OLD-path shim)
      3. `import scripts.earnings.builders.consensus` (canonical)

    All three MUST dispatch to the canonical _get_classifier() and return the
    SAME MarketSessionClassifier instance. The shim's globals().update() pins
    `_get_classifier` to the canonical function object; calling it from any
    path mutates the canonical module's `global _classifier` — a single cell.

    Without this guarantee, callers via different paths could see different
    classifier instances and inconsistent behavior. No external code imports
    `_classifier` directly today (verified by grep), but this test locks the
    invariant for the future.
    """
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


def test_classifier_singleton_attribute_access_across_paths():
    """Stage 7.1 REGRESSION GUARD for the shim mutable-snapshot bug.

    test_classifier_singleton_across_paths above proves the SINGLETON returned
    by `_get_classifier()` is identical across paths. This test goes one step
    further and proves DIRECT ATTRIBUTE ACCESS to `_classifier` also reflects
    canonical's current state across all paths.

    The bug fixed in Stage 7.1: the shim's eager-copy of `_classifier` at
    shim-import time captured the value `None`. After `_get_classifier()`
    mutated canonical's `_classifier`, the shim's `_classifier` snapshot
    stayed None — `build_consensus._classifier` and
    `scripts.earnings.build_consensus._classifier` returned None even though
    `scripts.earnings.builders.consensus._classifier` was the live instance.

    Fix: shim's PEP 562 `__getattr__` forwards `_classifier` (and any other
    name removed from shim globals) to canonical at access time. This test
    asserts the contract holds — direct attribute access yields the canonical
    singleton, not a stale snapshot.
    """
    import build_consensus as a
    import scripts.earnings.build_consensus as b
    import scripts.earnings.builders.consensus as c
    # Force initialization through any path
    cls = c._get_classifier()
    # Direct attribute access must return the canonical singleton from EVERY path.
    assert a._classifier is b._classifier is c._classifier is cls, (
        f"shim attribute stale: a={id(a._classifier)} "
        f"b={id(b._classifier)} c={id(c._classifier)} cls={id(cls)}"
    )


def test_xbrl_exact_splits_lazy_import_works():
    """REGRESSION GUARD for build_prior_financials's lazy outbound import.

    `scripts/earnings/builders/prior_financials.py` line ~1593 (was line 1593 in
    OLD) does:
        from xbrl_exact_splits import extract_segment_splits, build_revenue_splits_section
    inside `_build_revenue_splits_section()`. This is a LAZY import that fires
    only when the builder is called — silent failure mode if `ensure_legacy_paths()`
    didn't put EARNINGS_DIR on sys.path correctly.

    The xbrl_exact_splits module STAYS at scripts/earnings/xbrl_exact_splits.py
    (NOT moved into builders/). Stage 9 promotes the lazy import to a tested
    invariant: must resolve to the EARNINGS_DIR file with the expected functions.
    """
    import xbrl_exact_splits
    assert hasattr(xbrl_exact_splits, "extract_segment_splits"), \
        "xbrl_exact_splits missing extract_segment_splits"
    assert hasattr(xbrl_exact_splits, "build_revenue_splits_section"), \
        "xbrl_exact_splits missing build_revenue_splits_section"
    # Must resolve to scripts/earnings/, NOT the canonical builders/ subdir.
    assert "scripts/earnings/xbrl_exact_splits.py" in xbrl_exact_splits.__file__, (
        f"xbrl_exact_splits resolved to wrong location: {xbrl_exact_splits.__file__}"
    )


def test_classifier_appears_in_dir_across_paths():
    """Stage 7.2 REGRESSION GUARD for shim __dir__ completeness.

    The Stage 7.1 fix DELETED `_classifier` from the shim's __dict__ so
    PEP 562 `__getattr__` could forward access to canonical. That fixed
    `hasattr()` and direct attribute access — but it also removed
    `_classifier` from `dir(shim)` because PEP 562 `__getattr__` does NOT
    fire on `dir()` (which lists __dict__, not attribute lookups).

    Result of the gap (pre-Stage-7.2): `hasattr(build_consensus, "_classifier")`
    returned True, but `"_classifier" in dir(build_consensus)` returned False.
    Diverged from canonical (where both are True). Code that introspects via
    dir() (autocomplete, IDEs, sphinx, dir-driven tests) would see a smaller
    surface than canonical.

    Fix: shim now defines PEP 562 `__dir__()` returning the union of shim's
    own globals and `dir(_impl)`. This test asserts `_classifier in dir(mod)`
    for all three import paths.
    """
    import build_consensus as a
    import scripts.earnings.build_consensus as b
    import scripts.earnings.builders.consensus as c
    for mod, label in [(a, "build_consensus (bare)"),
                       (b, "scripts.earnings.build_consensus (qualified shim)"),
                       (c, "scripts.earnings.builders.consensus (canonical)")]:
        assert "_classifier" in dir(mod), (
            f"{label}: '_classifier' missing from dir() — "
            f"shim __dir__ forward broken? dir-len={len(dir(mod))}"
        )
