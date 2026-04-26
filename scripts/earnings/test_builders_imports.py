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
