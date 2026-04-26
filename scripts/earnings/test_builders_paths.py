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


def _run_in_fresh_subprocess(code: str) -> tuple[int, str, str]:
    """Helper: run `code` in a fresh Python subprocess so sys.modules + sys.path
    state are pristine. Returns (returncode, stdout, stderr)."""
    import subprocess
    res = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=30,
        # PYTHONPATH only — explicit value AFTER **environ to override.
        env={**os.environ, "PYTHONPATH": str(_paths.REPO_ROOT)},
    )
    return res.returncode, res.stdout, res.stderr


def test_utils_market_session_resolves_after_ensure_legacy_paths():
    """REGRESSION GUARD for the utils-shadow bug.

    `scripts/earnings/utils.py` is a single-file utility module that, under the
    legacy precedence order (SKILL > EARNINGS > SCRIPTS > REPO), would shadow
    the `utils/` PACKAGE at REPO_ROOT. Without the surgical pin in
    `_paths.ensure_legacy_paths()`, the lazy import
        `from utils.market_session import MarketSessionClassifier`
    inside build_consensus._get_classifier() and warmup_cache.build_inter_quarter_context()
    would fail at runtime with `ModuleNotFoundError: 'utils' is not a package`.

    This test runs in a FRESH subprocess so sys.modules is pristine — running
    in-process risks false-pass because earlier pytest collection imports may
    have already cached `utils` as the package via cwd-precedence. The test
    also runs `from utils.market_session import` IMMEDIATELY after
    `ensure_legacy_paths()` (no other path-mutating imports between) to ensure
    the fix works in the most adversarial ordering.
    """
    code = (
        "import sys\n"
        "from scripts.earnings.builders import _paths\n"
        "_paths.ensure_legacy_paths()\n"
        # IMMEDIATE — no intervening imports
        "from utils.market_session import MarketSessionClassifier\n"
        "import utils\n"
        # utils MUST be the package (has __path__), NOT scripts/earnings/utils.py (a single file)
        "assert hasattr(utils, '__path__'), f'utils not a package: {utils.__file__}'\n"
        "assert utils.__file__.endswith('utils/__init__.py'), \\\n"
        "    f'utils.__file__ wrong (expected utils/__init__.py, got {utils.__file__})'\n"
        "assert 'scripts/earnings/utils.py' not in utils.__file__, \\\n"
        "    f'utils accidentally resolved to the shadowing file: {utils.__file__}'\n"
        "print('utils.__file__ =', utils.__file__)\n"
        "print('OK')\n"
    )
    rc, stdout, stderr = _run_in_fresh_subprocess(code)
    assert rc == 0, f"failed:\nSTDOUT={stdout}\nSTDERR={stderr}"
    assert "OK" in stdout, f"missing OK marker:\n{stdout}"


def test_all_lazy_transitive_imports_resolve_in_fresh_subprocess():
    """Every lazy/transitive import inside builders MUST resolve after
    `ensure_legacy_paths()` in a FRESH subprocess (pristine sys.modules).

    The previous in-process version of this test could false-pass because
    earlier pytest collection imports mutated sys.modules. The fresh
    subprocess is the only way to verify behavior under the most adversarial
    ordering — what a real builder call would face on first cold dispatch.

    Catalog (verified by reconnaissance):
      - fiscal_math                       (consensus, prior_financials)
      - sec_quarter_cache_loader          (consensus, prior_financials)
      - xbrl_exact_splits                 (prior_financials lazy at line 1593)
      - guidance_ids                      (warmup_cache lazy at line 135)
      - utils.market_session              (consensus, warmup_cache) — see dedicated test above
      - neograph.Neo4jConnection          (all builders that touch Neo4j)
      - av_client                         (consensus top-level bare import)
      - pit_time                          (skill-scripts dir, used by pit_fetch)
    """
    code = (
        "from scripts.earnings.builders import _paths\n"
        "_paths.ensure_legacy_paths()\n"
        # All imports MUST succeed; if any fails, ensure_legacy_paths() is wrong.
        "import fiscal_math\n"
        "import sec_quarter_cache_loader\n"
        "import xbrl_exact_splits\n"
        "import guidance_ids\n"
        "from utils.market_session import MarketSessionClassifier\n"
        "from neograph.Neo4jConnection import get_manager\n"
        "import av_client\n"
        "import pit_time\n"
        "print('ALL_RESOLVE')\n"
    )
    rc, stdout, stderr = _run_in_fresh_subprocess(code)
    assert rc == 0, f"failed:\nSTDOUT={stdout}\nSTDERR={stderr}"
    assert "ALL_RESOLVE" in stdout
