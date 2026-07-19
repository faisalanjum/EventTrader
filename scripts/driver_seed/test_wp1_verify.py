"""Round-13: the verifier is CHECK-ONLY by default — an INVENTED extra output id fails, saved
manifest hashes are COMPARED (never silently replaced). `--record` is the explicit stamp mode,
run once after a deliberate regenerate.

    venv/bin/python -m pytest scripts/driver_seed/test_wp1_verify.py -q
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pytest
import wp1_verify as V


def test_reconcile_rejects_missing_and_invented():
    V._reconcile({'a', 'b'}, {'a', 'b'})
    with pytest.raises(AssertionError, match='NO id-carrying outcome'):
        V._reconcile({'a', 'b'}, {'a'})
    with pytest.raises(AssertionError, match='INVENTED'):
        V._reconcile({'a'}, {'a', 'zz'})
    print("[ok] reconciliation rejects both missing and invented ids")


def test_hash_check_requires_and_compares():
    V._expect_hashes({'x.jsonl': 'aa'}, {'x.jsonl': 'aa'})
    with pytest.raises(AssertionError, match='mismatch'):
        V._expect_hashes({'x.jsonl': 'aa'}, {'x.jsonl': 'bb'})
    with pytest.raises(AssertionError, match='no recorded hashes'):
        V._expect_hashes(None, {'x.jsonl': 'aa'})
    with pytest.raises(AssertionError, match='mismatch'):
        V._expect_hashes({'x.jsonl': 'aa'}, {'x.jsonl': 'aa', 'y.jsonl': 'cc'})
    print("[ok] check mode compares saved hashes, never restamps")
