"""DEPRECATED — 1-release alias for validate_learning.

The module was renamed as part of the obsidian_thinking unified-layout
commit (2026-04-17). The function name ``validate_attribution_result``
is UNCHANGED — it maps to schema ``attribution_result.v2`` which is also
unchanged (schema strings are preserved per plan).

Callers: ``from validate_attribution import validate_attribution_result``
continues to work via the ``*`` re-export below. Migrate at your leisure
to ``from validate_learning import validate_attribution_result``.

ABSOLUTE import, NOT relative — ``scripts/earnings/`` has no
``__init__.py`` and is loaded as a top-level module via ``sys.path``.
Using ``from .validate_learning import *`` would silently fail.
"""
from validate_learning import *  # noqa: F401, F403 — 1-release alias after module rename
