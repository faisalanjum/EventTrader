"""Focused retry-boundary tests; native replay is proved separately."""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import test_meaning_format_2105 as T
import meaning_retry_plan_2107 as M

G, B, F = T.G, T.B, T.F


@pytest.fixture
def saved(monkeypatch, tmp_path):
    B.bind_grading_scorer(str(Path(G.__file__).parent / 'scorers/score_exp5_current.py'),
                          G._sha_file(str(Path(G.__file__).parent / 'scorers/score_exp5_current.py')))
    values = [('native_true', True), ('native_false', False), ('native_null', None),
              ('quoted_true', 'true'), ('quoted_false', 'false'), ('quoted_null', 'null'),
              ('wrong_case', 'True')]
    rows = [{'lane_id': lane, 'batch_id': 'unfamiliar-batch'} for lane, _ in values]
    whole = {lane: json.dumps([{'question_id': 'unfamiliar-id',
                                'verdicts': dict.fromkeys(B.meaning_fields(), value)}])
             for lane, value in values}
    final = {'attempt': 1, 'validity': [[lane, not isinstance(value, str)] for lane, value in values],
             'retry': [lane for lane, value in values if isinstance(value, str)], 'uncalled': []}
    path = str(tmp_path / 'finalization.json')
    G._write_new(path, G._pretty(final) + '\n')
    monkeypatch.setattr(G, 'segment_state', lambda *_: 'finalized')
    monkeypatch.setattr(G, 'load_root', lambda *_: {'candidate_sha256': 'candidate'})
    monkeypatch.setattr(G, 'load_frozen', lambda *_: ({'task_kind': 'G2'}, 'candidate'))
    monkeypatch.setattr(G, 'whole_answers', lambda *_: (copy.deepcopy(whole), []))
    monkeypatch.setattr(G, 'load_receipt', lambda *_: {'rows': copy.deepcopy(rows)})
    monkeypatch.setattr(G, 'binding_and_parser', lambda *_: (lambda *_: {'question_ids': ['unfamiliar-id']}, None))
    monkeypatch.setattr(G, 'finalization_path', lambda *_: path)
    calls = []

    def finalizer(candidate, run, segment, root_sha, receipt_sha):
        calls.append((candidate, run, segment, root_sha, receipt_sha))
        G._write_new(path, G._pretty(final) + '\n')
        return copy.deepcopy(final), {}, []

    monkeypatch.setattr(G, 'finalize_segment', finalizer)
    args = ('candidate-dir', 'run-dir', 7, 'root', 'receipt',
            os.environ['A7_FORMAT_CODE_SHA256'], os.environ['A7_FORMAT_RULE_SHA256'])
    return args, final, path, calls


def test_complete_supported_population_keeps_only_genuinely_invalid_retry(saved):
    args, final, path, calls = saved
    original_write = G._write_new
    before = Path(path).read_bytes()
    result = M.plan(*args)
    assert result['retry_lanes'] == ['wrong_case']
    assert result['recovered'] == ['quoted_true', 'quoted_false', 'quoted_null']
    assert result['original_retry_lanes'] == final['retry']
    assert {row['lane_id']: next(iter(row['answer'].values()))[B.meaning_fields()[0]]
            for row in result['readings'] if row['answer'] is not None} == {
                'native_true': True, 'native_false': False, 'native_null': None,
                'quoted_true': True, 'quoted_false': False, 'quoted_null': None}
    assert calls == [args[:5]]
    assert Path(path).read_bytes() == before
    assert G._write_new is original_write


@pytest.mark.parametrize('failure', ['native refusal', 'accounting mismatch', 'receipt mismatch'])
def test_original_finalizer_errors_stop_retry_selection_with_positive_control(saved, monkeypatch, failure):
    args, *_ = saved
    original = G.finalize_segment
    assert M.plan(*args)['retry_lanes'] == ['wrong_case']
    monkeypatch.setattr(G, 'finalize_segment', lambda *_: (None, {}, [failure]))
    with pytest.raises(ValueError, match='original finalization refused'):
        M.plan(*args)
    monkeypatch.setattr(G, 'finalize_segment', original)
    assert M.plan(*args)['retry_lanes'] == ['wrong_case']


def test_changed_finalization_refuses_without_overwrite(saved):
    args, final, path, _ = saved
    assert M.plan(*args)['retry_lanes'] == ['wrong_case']
    original = Path(path).read_bytes()
    Path(path).write_text(G._pretty(dict(final, retry=[])) + '\n')
    changed = Path(path).read_bytes()
    with pytest.raises(ValueError, match='does not reproduce'):
        M.plan(*args)
    assert Path(path).read_bytes() == changed
    Path(path).write_bytes(original)
    assert M.plan(*args)['retry_lanes'] == ['wrong_case']


def test_original_validity_must_match_the_actual_parser(saved):
    args, final, path, _ = saved
    assert M.plan(*args)['retry_lanes'] == ['wrong_case']
    final['validity'][0][1] = False
    Path(path).write_text(G._pretty(final) + '\n')
    with pytest.raises(ValueError, match='original validity drifted'):
        M.plan(*args)


@pytest.mark.parametrize('boundary', ['unfinalized', 'other_kind', 'whole_missing'])
def test_each_early_boundary_refuses_after_real_positive(saved, monkeypatch, boundary):
    args, *_ = saved
    assert M.plan(*args)['retry_lanes'] == ['wrong_case']
    if boundary == 'unfinalized':
        monkeypatch.setattr(G, 'segment_state', lambda *_: 'published')
    elif boundary == 'other_kind':
        monkeypatch.setattr(G, 'load_frozen', lambda *_: ({'task_kind': 'G3'}, 'candidate'))
    else:
        monkeypatch.setattr(G, 'whole_answers', lambda *_: (None, ['missing whole']))
    with pytest.raises(ValueError):
        M.plan(*args)


def test_comparison_cannot_write_a_different_output(saved, monkeypatch, tmp_path):
    args, final, _, _ = saved
    assert M.plan(*args)['retry_lanes'] == ['wrong_case']
    unexpected = str(tmp_path / 'not-an-approved-output')
    def wrong_target(*_):
        G._write_new(unexpected, G._pretty(final))
    monkeypatch.setattr(G, 'finalize_segment', wrong_target)
    with pytest.raises(ValueError, match='does not reproduce'):
        M.plan(*args)
    assert not Path(unexpected).exists()


@pytest.mark.parametrize('command', ['ingest', 'retry', 'prepare'])
def test_cli_rejects_mutating_bootstrap_before_importing_or_running_it(command):
    result = subprocess.run([sys.executable, '-B', M.__file__], text=True, capture_output=True,
                            env={'A7_GRADING_COMMAND': command})
    assert result.returncode == 1
    assert 'only permits the read-only preflight bootstrap' in result.stderr
    assert 'ModuleNotFoundError' not in result.stderr


def test_cli_rejects_wrong_own_hash_before_bootstrap():
    result = subprocess.run([sys.executable, '-B', M.__file__], text=True, capture_output=True,
        env={'A7_GRADING_COMMAND': 'preflight', 'A7_RETRY_PLAN_SHA256': '0' * 64})
    assert result.returncode == 1
    assert 'unapproved retry-filter code' in result.stderr
