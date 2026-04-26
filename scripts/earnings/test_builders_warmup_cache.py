"""Tests for scripts.earnings.builders.warmup_cache."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[2]
# Use the running interpreter; `git worktree add` does NOT carry venv/.
PY = sys.executable

pytestmark = pytest.mark.builders


def test_module_test_flag_passes():
    """`python -m scripts.earnings.builders.warmup_cache --test` runs internal regression."""
    res = subprocess.run(
        [PY, "-m", "scripts.earnings.builders.warmup_cache", "--test"],
        capture_output=True, text=True, timeout=60,
        # Explicit value AFTER **os.environ so it overrides any inherited PYTHONPATH.
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    assert res.returncode == 0, f"--test failed: stdout={res.stdout!r} stderr={res.stderr!r}"
    # Verify the regression suite actually ran (not just exited 0)
    assert "passed" in (res.stdout + res.stderr).lower(), "no 'passed' marker in output"


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


def test_neograph_get_manager_resolves():
    """Smoke: the canonical module's `from neograph.Neo4jConnection import get_manager`
    must resolve via ensure_legacy_paths() — even before any Neo4j call is made."""
    from scripts.earnings.builders import warmup_cache as wc
    # The import must have succeeded for `get_manager` to be at module level
    assert hasattr(wc, "get_manager"), "neograph.Neo4jConnection.get_manager not imported"
