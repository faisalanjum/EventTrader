"""A path the world does not hold is absent, not the nearest file that shares a suffix.

`_resolve_source` fell back to any side-table key ending in the lookup's last two
components. Record 22655 asked for `HARNESS/driver/core/.claude/skills/.../fiscal_math.py`
- a path history never had - and was handed `HARNESS/.claude/skills/.../fiscal_math.py`
under the wrong name, which the module's own identity guard refused where history's
interpreter had simply skipped the missing directory.
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "ledger")]
import replay_transcript as RT  # noqa: E402


def test_a_lookup_is_answered_by_its_exact_path_only():
    side = {"/w/a/scripts/f.py": "A\n"}
    assert RT._resolve_source("/w/a/scripts/f.py", side, None) == "A\n"
    assert RT._resolve_source("/w/b/scripts/f.py", side, None) is None


def test_bodies_are_exact_too():
    bodies = {"/w/a/scripts/f.py": "B\n"}
    assert RT._resolve_source("/w/a/scripts/f.py", {}, None, bodies=bodies) == "B\n"
    assert RT._resolve_source("/w/c/scripts/f.py", {}, None, bodies=bodies) is None
