"""Static AST verification — old shim files must contain NO real business logic.

Permanent regression guard. If anyone re-introduces a `def build_*()` or `class`
in a shim file, this test fires immediately. The intent is "shim is shim-only;
all behavior lives in the canonical module".

PEP 562 hook exception: `def __getattr__(name)` and `def __dir__()` ARE allowed
because they are PEP 562 module-level hooks (shim machinery, not business logic).
build_consensus.py uses them to forward mutable globals like `_classifier` to
canonical (Stage 7.1 + 7.2 fixes).
"""
from __future__ import annotations
import ast
from pathlib import Path
import importlib.util
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

# CLI-capable shims must include `if __name__ == "__main__":`.
# builder_adapters.py is module-only (no main()) and is excluded.
CLI_CAPABLE = {
    REPO / "scripts/earnings/build_consensus.py",
    REPO / "scripts/earnings/build_prior_financials.py",
    REPO / "scripts/earnings/macro_snapshot.py",
    REPO / "scripts/earnings/peer_earnings_snapshot.py",
    REPO / ".claude/skills/earnings-orchestrator/scripts/warmup_cache.py",
}

# PEP 562 module hooks that are PERMITTED in shim files (machinery, not logic).
ALLOWED_FUNCTION_NAMES = {"__getattr__", "__dir__"}


pytestmark = pytest.mark.builders


@pytest.mark.parametrize("shim_path", SHIM_FILES, ids=lambda p: p.name)
def test_shim_has_no_business_function_def(shim_path):
    """Shim files must contain NO `def`s except PEP 562 hooks (__getattr__, __dir__)."""
    tree = ast.parse(shim_path.read_text())
    forbidden = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name not in ALLOWED_FUNCTION_NAMES
    ]
    assert not forbidden, (
        f"{shim_path.name} contains forbidden FunctionDef nodes: "
        f"{[f.name for f in forbidden]}"
    )


@pytest.mark.parametrize("shim_path", SHIM_FILES, ids=lambda p: p.name)
def test_shim_has_no_class_def(shim_path):
    """Shim files must contain NO `class` definitions."""
    tree = ast.parse(shim_path.read_text())
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    assert not classes, (
        f"{shim_path.name} contains ClassDef nodes: {[c.name for c in classes]}"
    )


@pytest.mark.parametrize("shim_path", SHIM_FILES, ids=lambda p: p.name)
def test_shim_references_canonical_package(shim_path):
    """Shim files must import from `scripts.earnings.builders` (proves they
    actually delegate to canonical, not silently no-op)."""
    text = shim_path.read_text()
    assert "scripts.earnings.builders" in text, (
        f"{shim_path.name} does not reference scripts.earnings.builders"
    )


@pytest.mark.parametrize("shim_path", sorted(CLI_CAPABLE), ids=lambda p: p.name)
def test_cli_shim_has_main_block(shim_path):
    """CLI-capable shims (builders that originally had `if __name__ == \"__main__\"`)
    must keep that block so `python3 path/to/shim.py ARGS` still dispatches to
    canonical's main()."""
    text = shim_path.read_text()
    assert ('__name__ == "__main__"' in text or "__name__ == '__main__'" in text), (
        f"{shim_path.name} is CLI-capable but missing __main__ block"
    )


@pytest.mark.parametrize("shim_path", SHIM_FILES, ids=lambda p: p.name)
def test_shim_all_excludes_underscore_names(shim_path):
    """`__all__` in every shim must EXCLUDE underscore-prefixed names so that
    `from <shim> import *` retains the same wildcard surface as the canonical
    module had before relocation.

    Underscore names are still bound to the shim's globals via the eager-copy
    loop (so `from <shim> import _priv` works) — they are just absent from
    `__all__`. This preserves the OLD wildcard semantics: only public names,
    no private leakage.

    If this test fails, someone reverted the shim template to the simpler
    `__all__ = [n for n in dir(_impl) if not n.startswith("__")]` which would
    leak underscore names through `*`-import.
    """
    spec = importlib.util.spec_from_file_location(
        f"_shim_test_{shim_path.stem}", shim_path,
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    underscored = [n for n in mod.__all__ if n.startswith("_")]
    assert not underscored, (
        f"{shim_path.name} __all__ leaks underscore names: {underscored}. "
        f"Fix the shim template per §5 — `__all__` line must filter on "
        f"`not _name.startswith('_')`, not `not _name.startswith('__')`."
    )
