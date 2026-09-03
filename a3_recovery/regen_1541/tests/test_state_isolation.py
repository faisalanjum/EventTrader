"""Every runner must hand back the caches it was given (Codex SEQ 1556 item 1).

A shallow module snapshot cannot undo a cleared cache, so a case that empties
`_SIBLING_CACHE` or `_LEDGERS` used to leave the next case measuring against state it
had destroyed. These controls seed a UNIQUE sentinel in every discovered cache, run the
real runners, and require every sentinel to survive - identity and contents both.
"""
import contextlib
import io
import os
import sys

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "ledger"))
sys.path.insert(0, _R)
import chrono_replay as CR                                     # noqa: E402
import replay_transcript as RT                                 # noqa: E402
import replay_caches                                           # noqa: E402
import mutations as MU                                         # noqa: E402

MODULES = (CR, RT)


def _seed():
    """Put one unique sentinel in every discovered cache -> {id(container): sentinel}."""
    marks = {}
    for _m, name, obj in replay_caches.caches(MODULES):
        mark = "SENTINEL::%s" % name
        if isinstance(obj, dict):
            obj[mark] = mark
        elif isinstance(obj, set):
            obj.add(mark)
        else:
            obj.append(mark)
        marks[id(obj)] = (name, mark, obj)
    return marks


def _survivors(marks):
    return [name for name, mark, obj in marks.values() if mark not in obj]


def _clear_marks(marks):
    for _name, mark, obj in marks.values():
        if isinstance(obj, dict):
            obj.pop(mark, None)
        elif isinstance(obj, set):
            obj.discard(mark)
        elif mark in obj:
            obj.remove(mark)


def test_every_replay_cache_is_discovered_not_hand_listed():
    """A hand list is what went stale before; the guard must FIND the caches."""
    names = {name for _m, name, _o in replay_caches.caches(MODULES)}
    for required in ("_SIBLING_CACHE", "_LAST_RESOLVED", "_SCRIPT_CACHE", "_LEDGERS"):
        assert required in names, (required, sorted(names))


def test_a_cleared_cache_is_restored_with_its_ORIGINAL_object():
    """Identity as well as contents: a closure captured at import time holds the
    original container, so handing the module a fresh dict would strand it."""
    before = CR._SIBLING_CACHE
    marks = _seed()
    try:
        with replay_caches.preserved(*MODULES):
            CR._SIBLING_CACHE.clear()
            RT._LEDGERS.clear()
            CR._SIBLING_CACHE[("leak", 0)] = "MUST NOT SURVIVE"
        assert CR._SIBLING_CACHE is before
        assert _survivors(marks) == [], _survivors(marks)
        # RESTORING IS NOT MERELY REFILLING. Updating the cache without clearing it
        # first leaves everything the fenced run added, so the next run inherits it.
        assert ("leak", 0) not in CR._SIBLING_CACHE, "the fenced run's entry survived"
    finally:
        _clear_marks(marks)


def test_the_MUTATION_HARNESS_hands_back_every_cache():
    """The case that clears the ledger is the one that used to poison later rows."""
    marks = _seed()
    # THE MODULE SNAPSHOT TOO, exactly as the real runner does it. `_call` fences the
    # CACHES; a case invoked with mutate=True also INSTALLS a fault, and without the
    # module restore that mutant callable leaks into the rest of the session - which is
    # how this control briefly broke an unrelated script-cache test.
    shot = MU._snapshot()
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            MU._call(MU.case_resume_agrees_with_past_route, False)
            MU._call(MU.case_script_cache_per_cutoff, True)
        assert _survivors(marks) == [], _survivors(marks)
    finally:
        MU._restore(shot)
        _clear_marks(marks)


def test_a_FAULT_that_clears_a_cache_still_hands_it_back():
    """`ledger accounts for every row` clears `_LEDGERS` as it installs, on purpose."""
    marks = _seed()
    shot = MU._snapshot()
    try:
        with replay_caches.preserved(*MODULES):
            with MU.FAULTS["ledger accounts for every row"].applied(True):
                pass
        assert _survivors(marks) == [], _survivors(marks)
    finally:
        MU._restore(shot)
        _clear_marks(marks)


def test_a_fault_against_a_NEW_owner_cannot_leak():
    """Declaring a fault must extend the restore set, by construction.

    The class defect: `_snapshot()` used to name its modules by hand, so a fault
    declared against a module nobody had added to that list stayed installed for every
    later case. The set is now DERIVED from the registry's own targets, which this
    control proves by inventing an owner that no hand list could have known about.
    """
    import types
    probe = types.ModuleType("zz_probe_owner")
    probe.value = "ORIGINAL"
    MU.Fault.ALIASES["ZZ"] = probe                 # a brand-new mutable owner
    MU.fault("a temporary probe fault", "ZZ.value",
             lambda saved: "MUTANT", note="exists only inside this control")
    try:
        assert probe in [m for m, _v in MU._snapshot()], \
            "the derived snapshot set does not cover a newly declared owner"
        shot = MU._snapshot()
        MU.FAULTS["a temporary probe fault"].install()
        assert probe.value == "MUTANT", "the fault did not install"
        MU._restore(shot)
        assert probe.value == "ORIGINAL", "the mutant leaked past the restore"
    finally:
        MU.FAULTS.pop("a temporary probe fault", None)
        MU.Fault.ALIASES.pop("ZZ", None)
