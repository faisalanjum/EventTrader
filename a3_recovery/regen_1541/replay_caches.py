"""Save and restore the replay's mutable caches EXACTLY (Codex SEQ 1556 item 1).

A shallow module snapshot cannot undo a CLEARED cache. `dict(vars(module))` captures
the same dict OBJECT, so after `cache.clear()` the snapshot and the live module hold
one identical, empty container: `is not` sees nothing to restore, and every entry that
existed before the run is gone. The next case then runs against a cache some earlier
case emptied, which is not an isolated measurement.

The caches are DISCOVERED, not listed. Any module-level mutable container in the
modules handed in is preserved, so a cache added later is covered without editing this
file - and a hand list is exactly what went stale in the append census.
"""
import contextlib


def caches(modules):
    """-> [(module, name, container)] for every module-level mutable container."""
    found = []
    for module in modules:
        for name, value in sorted(vars(module).items()):
            if name.startswith("__"):
                continue
            if isinstance(value, (dict, set, list)):
                found.append((module, name, value))
    return found


@contextlib.contextmanager
def preserved(*modules):
    """Restore both object IDENTITY and exact contents of every discovered cache.

    The containers themselves are kept and refilled rather than reassigned, because a
    closure captured at import time holds the original object: handing the module a
    fresh dict would leave that closure reading a cache nobody else writes.
    """
    saved = [(obj, obj.copy()) for _m, _n, obj in caches(modules)]
    try:
        yield
    finally:
        for obj, before in saved:
            obj.clear()
            if isinstance(obj, list):
                obj.extend(before)
            else:
                obj.update(before)
