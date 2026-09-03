"""A route computed once is served from disk under the same key as the sibling cache.

Every fresh namespace - each mutation, each audited row - recomputed every route by
rescanning the 210 MB transcript, which made the mutation step and the audit fifteen
times slower than before this round's route rules. The route cache stores the record
line numbers of a computed route under a key bound to the replay code, the accepted
transcript identity and the git store identity (the same digest the sibling cache
uses); the chain empties the cache before it starts, so nothing built against other
inputs is ever served.
"""
import hashlib
import os
import sys

R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [os.path.join(R, "ledger")]
import chrono_replay as CR  # noqa: E402

OWNER = "bench_1306/.claude/plans/Drivers/experiments/harness/raw_transport.py"


def test_a_computed_route_is_served_from_disk_under_the_input_digest():
    key = CR.route_cache_path(OWNER, 22310, 22400)
    assert os.path.basename(key).startswith("route_") and CR._code_digest() in os.path.basename(key)
    if os.path.exists(key):
        os.remove(key)
    CR._RECORD_INDEX.pop((OWNER, 22310, 22400), None)
    first = [n for n, _r in CR.modifying_records(OWNER, 22310, 22400)]
    assert os.path.isfile(key)                                  # written once
    CR._RECORD_INDEX.pop((OWNER, 22310, 22400), None)           # a fresh namespace
    again = [n for n, _r in CR.modifying_records(OWNER, 22310, 22400)]
    assert again == first
    assert all(isinstance(r, dict) and r.get("message") for _n, r in CR.modifying_records(OWNER, 22310, 22400))


def test_the_key_changes_with_the_inputs():
    a = CR.route_cache_path(OWNER, 1, 10)
    b = CR.route_cache_path(OWNER, 1, 11)
    c = CR.route_cache_path("other/name.py", 1, 10)
    assert len({a, b, c}) == 3


def test_no_disk_cache_write_comes_from_a_mutant_namespace():
    """While a fault is installed the caches only read; the harness restore re-enables writes."""
    import shutil
    sys.path.insert(0, R); sys.path.insert(0, os.path.join(R, "proofs"))
    import mutations as M
    shot = M._snapshot()
    try:
        M.FAULTS["a lookup is answered by a suffix match"].install()
        assert CR.DISK_CACHE_WRITES is False
        key = CR.route_cache_path(OWNER, 22310, 22330)
        if os.path.exists(key):
            os.remove(key)
        CR._RECORD_INDEX.pop((OWNER, 22310, 22330), None)
        CR.modifying_records(OWNER, 22310, 22330)
        assert not os.path.exists(key)                        # computed, not written
    finally:
        M._restore(shot)
    assert CR.DISK_CACHE_WRITES is True
