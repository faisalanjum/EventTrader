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


def test_determinism_validation_requires_two_distinct_complete_seeds():
    """Round-20 (reviewer): zero or one seed run must FAIL; exactly two runs with DISTINCT seeds,
    each complete and matching the stamped hashes, pass."""
    H = {f'f{i}.jsonl': f'h{i}' for i in range(8)}
    good = {'output_sha256': H, 'code_commit': 'abc1234',
            'determinism_proof': {'commit': 'abc1234', 'runs': [
        {'PYTHONHASHSEED': 1, 'sha256': dict(H)}, {'PYTHONHASHSEED': 2, 'sha256': dict(H)}]}}
    V._validate_determinism(good)
    for bad_runs in ([],
                     [{'PYTHONHASHSEED': 1, 'sha256': dict(H)}],
                     [{'PYTHONHASHSEED': 1, 'sha256': dict(H)}, {'PYTHONHASHSEED': 1, 'sha256': dict(H)}],
                     [{'PYTHONHASHSEED': 1, 'sha256': dict(H)}, {'PYTHONHASHSEED': 2, 'sha256': {'f0.jsonl': 'h0'}}]):
        try:
            V._validate_determinism({'output_sha256': H, 'code_commit': 'abc1234',
                                     'determinism_proof': {'commit': 'abc1234', 'runs': bad_runs}})
            raise SystemExit(f"accepted invalid runs: {bad_runs}")
        except AssertionError:
            pass
    try:
        V._validate_determinism({'output_sha256': H})
        raise SystemExit("accepted a manifest with NO determinism proof")
    except AssertionError:
        pass
    print("[ok] determinism proof: exactly two distinct complete matching seed runs required")


def test_slice_literal_bytes_catch_reordering(tmp_path):
    """Round-22: the LITERAL-bytes hash must change when lines are reordered (the canonical
    row-set sha alone cannot see order)."""
    a = tmp_path / 'a.jsonl'; b = tmp_path / 'b.jsonl'
    a.write_text('{"r":1}\n{"r":2}\n'); b.write_text('{"r":2}\n{"r":1}\n')
    assert V.sha(str(a)) != V.sha(str(b))
    print("[ok] byte-reordered input yields a different literal hash")


def test_dirt_paths_cover_every_imported_root():
    """Round-22: the dirt check must name every code root the run imports."""
    assert set(V.DIRT_PATHS) == {'scripts/driver_seed', 'driver/relocation', 'scripts/earnings',
                                 '.claude/skills/earnings-orchestrator'}, V.DIRT_PATHS
    print("[ok] all four imported code roots in the dirt check")


def test_record_validates_before_writing():
    """Round-22: in --record mode the two-seed validation must execute BEFORE the manifest or
    report is written (source-order assertion on the record branch)."""
    src = open(V.__file__).read()
    rec = src[src.index("if a.record:", src.index("def main")):]
    assert rec.index('_validate_determinism') < rec.index("json.dump(man, open(MAN"), \
        "RECORD writes before validating the determinism proof"
    assert rec.index('_validate_determinism') < rec.index("open(REPORT, 'w')")
    print("[ok] RECORD validates the proof before any write")


def test_proof_commit_must_equal_stamp_commit():
    """Round-22: the determinism proof's commit must match the manifest's code_commit."""
    H = {'f.jsonl': 'h'}
    good = {'output_sha256': H, 'code_commit': 'abc1234',
            'determinism_proof': {'commit': 'abc1234', 'runs': [
                {'PYTHONHASHSEED': 1, 'sha256': dict(H)},
                {'PYTHONHASHSEED': 2, 'sha256': dict(H)}]}}
    V._validate_determinism(good)
    bad = {**good, 'code_commit': 'zzz9999'}
    try:
        V._validate_determinism(bad)
        raise SystemExit("accepted a proof pinned to a different commit")
    except AssertionError:
        pass
    print("[ok] proof commit == stamp commit enforced")


def test_proof_commit_exact_equality_never_prefix():
    """Round-23 (reviewer): '8' must NOT satisfy '86c8f44' — exact equality (with or without
    the -dirty suffix), never startswith."""
    H = {'f.jsonl': 'h'}
    def man(cc, pc):
        return {'output_sha256': H, 'code_commit': cc,
                'determinism_proof': {'commit': pc, 'runs': [
                    {'PYTHONHASHSEED': 1, 'sha256': dict(H)},
                    {'PYTHONHASHSEED': 2, 'sha256': dict(H)}]}}
    V._validate_determinism(man('86c8f44', '86c8f44'))
    V._validate_determinism(man('86c8f44-dirty', '86c8f44'))
    for cc, pc in [('86c8f44', '8'), ('86c8f44', '86c8f4'), ('86c8f44x', '86c8f44')]:
        try:
            V._validate_determinism(man(cc, pc))
            raise SystemExit(f"prefix/partial commit accepted: {cc} vs {pc}")
        except AssertionError:
            pass
    print("[ok] proof commit equality is exact, never prefix")


def test_verifier_rejects_reordered_slice(tmp_path, monkeypatch):
    """Round-23 (reviewer): prove THE VERIFIER rejects a byte-reordered slice — not merely that
    two hashes differ."""
    sl = tmp_path / 'slice.jsonl'
    sl.write_text('{"r": 1}\n{"r": 2}\n')
    monkeypatch.setattr(V, 'SLICE_FILE', str(sl))
    man = {'slice_file_sha256': V.sha(str(sl))}
    V._check_slice_bytes(man)                        # ordered file passes
    sl.write_text('{"r": 2}\n{"r": 1}\n')            # same rows, reordered bytes
    try:
        V._check_slice_bytes(man)
        raise SystemExit("verifier accepted a byte-reordered slice")
    except AssertionError:
        pass
    print("[ok] the verifier itself rejects reordered input")
