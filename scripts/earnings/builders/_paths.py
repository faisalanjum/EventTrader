"""Centralized repo-root + sys.path discipline for the builders subpackage.

Every canonical builder module imports from this helper. Old files using
Path(__file__).resolve().parents[2] historically assumed the file lived at
scripts/earnings/<X>.py; the same expression breaks at scripts/earnings/builders/<X>.py.
This module eliminates that risk by computing paths from THIS file's location
(parents[3] from scripts/earnings/builders/_paths.py = repo root).
"""
from __future__ import annotations

import sys
from pathlib import Path

# parents[0] = builders, parents[1] = earnings, parents[2] = scripts, parents[3] = repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
EARNINGS_DIR = REPO_ROOT / "scripts" / "earnings"
SKILL_SCRIPTS_DIR = REPO_ROOT / ".claude" / "skills" / "earnings-orchestrator" / "scripts"
ENV_PATH = REPO_ROOT / ".env"


def ensure_legacy_paths() -> None:
    """Insert the four directories that builders historically relied on, in
    the EXACT precedence order builder_adapters.py used.

    Current builder_adapters.py inserts repo root, then scripts/earnings, then
    .claude/.../scripts each at index 0, leaving effective precedence:
      skill-scripts > earnings-local > scripts/ > repo root.

    This function reproduces that precedence exactly while being idempotent
    (calling it twice does not duplicate entries) and deterministic under
    pytest, direct CLI execution, python -m, and old sys.path-mutating scripts.
    """
    desired = (SKILL_SCRIPTS_DIR, EARNINGS_DIR, SCRIPTS_DIR, REPO_ROOT)
    for path in desired:
        s = str(path)
        while s in sys.path:
            sys.path.remove(s)
    for path in reversed(desired):
        sys.path.insert(0, str(path))


def skill_script(name: str) -> str:
    """Resolve a path to a script file inside the earnings-orchestrator skill."""
    return str(SKILL_SCRIPTS_DIR / name)
