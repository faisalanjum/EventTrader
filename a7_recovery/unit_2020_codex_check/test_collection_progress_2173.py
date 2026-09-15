"""The collection report must distinguish lanes, attempts and batch files."""
import contextlib
import io
import json
from pathlib import Path

import pytest


SUBJECT = Path(__file__).parents[1] / 'unit_2173_grading/collection_progress_2173.py'


def report(tmp_path, retried, grouped=True, retry_valid=True):
    unit = tmp_path / 'unit_2173_grading'
    run = unit / 'G2/run'
    candidate = (tmp_path / 'unit_2020_codex_check/codex_changedprep2171_a'
                 / 'G2/a7_g1_candidate.json')
    lanes = ['G2-000/G1a', 'G2-000/G1b', 'G2-001/G1a', 'G2-001/G1b']

    def save(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')

    save(run / 'root.json', {'rows': [{'lane_id': lane} for lane in lanes],
                             'max_attempts': 2})
    save(candidate, {'questions': 5, 'batch_rows': [
        {'batch_id': 'G2-000', 'items': 2},
        {'batch_id': 'G2-001', 'items': 3}]})
    segments = ([(1, 1, lanes[:2], [True, True]),
                 (2, 1, lanes[2:], [True, False])] if grouped else
                [(i + 1, 1, [lane], [i != 3])
                 for i, lane in enumerate(lanes)])
    if retried:
        segments.append((len(segments) + 1, 2, lanes[3:], [retry_valid]))
    ledger = []
    for segment, attempt, selected, validity in segments:
        suffix = 'seg%02d.json' % segment
        save(run / ('receipt.' + suffix), {'segment': segment})
        save(run / ('invocation.' + suffix), {'args': [
            {'lane_id': lane, 'attempt': attempt} for lane in selected]})
        invalid = [lane for lane, ok in zip(selected, validity) if not ok]
        save(run / ('finalization.' + suffix), {
            'attempt': attempt, 'validity': list(zip(selected, validity)),
            'problems': {lane: ['invalid reading'] for lane in invalid},
            'retry': invalid if attempt == 1 else []})
        ledger.append({'kind': 'G2', 'segment': segment,
                       'run_id': 'fixture_%d' % segment})
    (unit / 'COLLECTION_LEDGER_2173.jsonl').write_text(
        ''.join(json.dumps(row) + '\n' for row in ledger), encoding='utf-8')
    # Execute the ACTUAL helper bytes in a disposable fixture tree; its normal
    # file-relative paths resolve there. Never run against Core's live files.
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(SUBJECT.read_text(), str(SUBJECT), 'exec'),
             {'__file__': str(unit / 'collection_progress_2173.py'),
              '__name__': '__main__'})
    return json.loads((unit / 'COLLECTION_PROGRESS_2173.json').read_text())


@pytest.mark.parametrize('retried', [False, True])
@pytest.mark.parametrize('field', ['lanes_scheduled', 'lanes_launched'])
def test_multi_lane_batches_and_retries_do_not_change_lane_denominator(tmp_path, retried, field):
    actual = report(tmp_path, retried)
    assert actual['total']['lanes_required'] == 4
    assert actual['total'][field] == 4
    assert actual['per_kind']['G2'][field] == 4


@pytest.mark.parametrize('field,empty', [('retry_eligible_lanes', []), ('problems', {})])
def test_retry_is_open_before_recovery_but_not_after_success(tmp_path, field, empty):
    before = report(tmp_path / 'before', False)['per_kind']['G2']
    assert before['lanes_usable'] == 3
    assert before['retry_eligible_lanes'] == ['G2-001/G1b']
    assert before['problems'] == {'G2-001/G1b': ['invalid reading']}
    after = report(tmp_path / 'after', True)['per_kind']['G2']
    assert after['lanes_usable'] == after['lanes_finalized'] == 4
    assert after['lanes_invalid'] == after['lanes_exhausted'] == 0
    assert after[field] == empty


def test_one_lane_per_segment_is_a_real_positive_control(tmp_path):
    actual = report(tmp_path, False, grouped=False)['total']
    assert actual['lanes_scheduled'] == actual['lanes_launched'] == 4
    assert actual['lanes_required'] == 4


def test_exhausted_invalid_is_not_offered_a_third_attempt(tmp_path):
    actual = report(tmp_path, True, retry_valid=False)['per_kind']['G2']
    assert actual['lanes_usable'] == 3
    assert actual['lanes_invalid'] == actual['lanes_exhausted'] == 1
    assert actual['retry_eligible_lanes'] == []
    assert actual['problems'] == {'G2-001/G1b': ['invalid reading']}
    assert actual['questions_covered_by_usable_lanes'] == 2


def test_question_coverage_requires_both_valid_readings(tmp_path):
    before = report(tmp_path / 'before', False)
    after = report(tmp_path / 'after', True)
    assert before['total']['questions_required'] == after['total']['questions_required'] == 5
    assert before['total']['questions_covered_by_usable_lanes'] == 2
    assert after['total']['questions_covered_by_usable_lanes'] == 5


@pytest.mark.parametrize('before,after,field,expected', [
    ("('lanes_scheduled', len(scheduled_lanes))",
     "('lanes_scheduled', len(scheduled))", 'lanes_scheduled', 4),
    ("('lanes_launched', len(launched_lanes))",
     "('lanes_launched', sum(1 for k, s in runs if k == kind))",
     'lanes_launched', 4),
    ("retry = [l for l in invalid if standing[l][0] < root['max_attempts']]",
     "retry = sorted({lane for path in glob.glob(os.path.join(run, "
     "'finalization.seg*.json')) for lane in read(path).get('retry', [])})",
     'retry_eligible_lanes', []),
    ("problems = {l: problems[l] for l in invalid if l in problems}",
     "# mutant retains historical problems", 'problems', {}),
])
def test_actual_counter_and_retry_regressions_are_detected(
        tmp_path, monkeypatch, before, after, field, expected):
    source = SUBJECT.read_text()
    assert source.count(before) == 1
    mutant = tmp_path / 'mutant.py'
    mutant.write_text(source.replace(before, after), encoding='utf-8')
    monkeypatch.setitem(globals(), 'SUBJECT', mutant)
    actual = report(tmp_path / 'run', True)['per_kind']['G2']
    # The helper must execute normally; the independent four-lane fixture
    # then detects the wrong result. An unrelated crash is not a killed mutant.
    assert actual[field] != expected
