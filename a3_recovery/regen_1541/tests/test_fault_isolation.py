"""A recompiled fault touches ONE symbol and nothing the module body installs elsewhere.

`recompiled()` executes the module's source into a fresh namespace; chrono_replay's
body installs four hooks into replay_transcript at import (SIBLING_RESOLVER,
TREE_COMMIT, TREE_MODIFIED, SELECT_UNITS), so every recompiled chrono fault re-pointed
those hooks at the mutant namespace and the revert put back only the targeted
attribute. The append fault then left SELECT_UNITS calling a mutant `_python_writes`,
and an unrelated control failed inside the audit (row "a command starts in its record's
directory") while passing alone.
"""
import glob
import importlib
import os
import sys

R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [os.path.join(R, "ledger"), R, os.path.join(R, "proofs")]
import chrono_replay as CR  # noqa: E402
import replay_transcript as RT  # noqa: E402
import replay_caches  # noqa: E402
import mutations as MU  # noqa: E402

HOOKS = ("SIBLING_RESOLVER", "TREE_COMMIT", "TREE_MODIFIED", "SELECT_UNITS")


def test_a_recompiled_fault_leaves_the_transcript_hooks_untouched():
    before = {h: getattr(RT, h) for h in HOOKS}
    with replay_caches.preserved(CR, RT), MU.FAULTS["an append is not a write"].applied(True):
        assert CR.DISK_CACHE_WRITES is False           # read-only while the fault is applied
    after = {h: getattr(RT, h) for h in HOOKS}
    assert all(after[h] is before[h] for h in HOOKS), [h for h in HOOKS if after[h] is not before[h]]
    assert CR.DISK_CACHE_WRITES is True                # and writable again afterwards


def test_the_record_directory_control_still_passes_after_the_append_fault():
    with replay_caches.preserved(CR, RT), MU.FAULTS["an append is not a write"].applied(True):
        pass
    mod = importlib.import_module("test_replay_world") if "test_replay_world" in sys.modules else None
    if mod is None:
        sys.path.insert(0, os.path.join(R, "tests"))
        mod = importlib.import_module("test_replay_world")
    with replay_caches.preserved(CR, RT):
        mod.test_a_command_without_cd_stood_in_the_records_working_directory()
