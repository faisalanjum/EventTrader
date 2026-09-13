"""Batch-size boundary tests; all source/question content must survive."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_g23_run as GR
import a7_g1_workflow_gate as W


def packet(_bid, batch):
    return {'prompt': G._pretty(batch),
            'question_ids': [item['id'] for _sid, item in batch]}


def size(bid, text, ordinal):
    return max(len(G._bound_script([{'lane_id': bid + '/' + lane, 'batch_id': bid,
                                    'ordinal': ordinal, 'prompt': text,
                                    'prompt_sha256': G._sha(text)}],
                                   {'candidate_sha256': '0' * 64}, '0' * 64, 1).encode('utf-8'))
               for lane in G.GRADER_LANES)


def rows(count, payload):
    return [('unfamiliar-source-' + str(n), {'id': 'question-' + str(n), 'source': payload})
            for n in range(count)]


def test_small_batch_and_empty_population_remain_unchanged():
    original = rows(3, 'ordinary source')
    result, prompts, mapping = GR._rows_and_prompts('G2', [original], packet)
    assert [row['items'] for row in result] == [3]
    assert prompts == {'G2-000': packet('G2-000', original)['prompt']}
    assert mapping == {item['id']: 'G2-000' for _sid, item in original}
    assert GR._rows_and_prompts('G3', [], packet) == ([], {}, {})


@pytest.mark.parametrize('kind', ['G2', 'G3'])
@pytest.mark.parametrize('payload', ['unfamiliar ' * 200, '\"\\\n\t漢🙂' * 200], ids=['plain', 'escaped_unicode'])
def test_oversized_batch_is_split_without_dropping_or_changing_any_question(monkeypatch, kind, payload):
    original = rows(10, payload)
    before = copy.deepcopy(original)
    # Independent limit allows two such records, not ten. The expected
    # population comes from the input, never from the grouping function.
    cap = size(kind + '-000', packet('', original[:2])['prompt'], 19)
    monkeypatch.setattr(W, 'SCRIPT_BYTE_LIMIT', cap)
    result, prompts, mapping = GR._rows_and_prompts(kind, [original], packet)
    assert len(result) > 1
    assert original == before
    assert sum(row['items'] for row in result) == len(original)
    assert set(mapping) == {item['id'] for _sid, item in original}
    recovered = []
    for n, row in enumerate(result):
        text = prompts[row['batch_id']]
        assert size(row['batch_id'], text, n * len(G.GRADER_LANES) + len(G.GRADER_LANES) - 1) <= cap
        assert len(row['source_ids']) == len(set(row['source_ids']))
        recovered.extend(json.loads(text))
    assert recovered == [[sid, item] for sid, item in original]


def test_one_oversized_question_refuses_without_truncation(monkeypatch):
    original = rows(1, 'source must not be trimmed' * 300)
    amount = size('G2-000', packet('', original)['prompt'], len(G.GRADER_LANES) - 1)
    monkeypatch.setattr(W, 'SCRIPT_BYTE_LIMIT', amount - 1)
    with pytest.raises(ValueError, match='transport'):
        GR._rows_and_prompts('G2', [original], packet)
    # The same exact content is a positive control at the exact byte boundary.
    monkeypatch.setattr(W, 'SCRIPT_BYTE_LIMIT', amount)
    result, prompts, _ = GR._rows_and_prompts('G2', [original], packet)
    assert len(result) == 1 and prompts['G2-000'] == packet('', original)['prompt']


def test_final_candidate_counts_the_actual_split_batches(monkeypatch):
    original = rows(10, 'distinct source content ' * 200)
    g2 = {'P1|' + sid: [(n, n)] for n, (sid, _item) in enumerate(original)}
    g3 = {'P1|' + sid: [n] for n, (sid, _item) in enumerate(original)}
    by_source = dict(original)
    def build(_gold, _arms, batch, *_rest):
        return packet('', [(sid, by_source[sid.split('|', 1)[1]]) for sid, _ in batch])
    monkeypatch.setattr(GR, 'populations', lambda *_args, **_kwargs:
                        (g2, g3, {}, {}, {}, [], [], {}))
    monkeypatch.setattr(GR, '_g2_packet_for', build)
    monkeypatch.setattr(GR, '_g3_packet_for', build)
    monkeypatch.setattr(G, 'live_key', lambda: ({}, {}))
    cap = size('G2-000', packet('', original[:2])['prompt'], 19)
    monkeypatch.setattr(W, 'SCRIPT_BYTE_LIMIT', cap)
    doc, prompts, problems = GR.freeze('TEST producer', inputs={'verified': 'TEST'}, g1={'pins': {}})
    assert not problems
    for kind in ('G2', 'G3'):
        selected = [row for row in doc['batching']['rows'] if row['batch_id'].startswith(kind + '-')]
        assert len(selected) > 1
        assert doc[kind.lower()]['questions'] == sum(r['items'] for r in selected) == 10
        assert doc[kind.lower()]['batches'] == len(selected)
        assert doc[kind.lower()]['largest_batch'] == max(r['items'] for r in selected)
        assert doc['remaining_calls'][kind.lower()] == len(selected) * len(G.GRADER_LANES)
    assert doc['batching']['batches'] == len(prompts)
    assert doc['remaining_calls']['total'] == len(prompts) * len(G.GRADER_LANES)


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q', '-p', 'no:cacheprovider']))
