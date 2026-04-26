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
