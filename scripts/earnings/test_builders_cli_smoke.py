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
    return subprocess.run(
        argv, check=True, timeout=timeout, capture_output=True, text=True,
        # Explicit value AFTER **os.environ so it overrides any inherited PYTHONPATH.
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
