"""Independent arithmetic/accounting checks on the completed TEST lifecycle.

Reads frozen inputs and raw TEST judgments. Does not import any scorer,
matcher, finalizer or gate, and makes no claim about real model meaning.
"""
import collections
from decimal import Decimal
import json
from pathlib import Path

root = Path(__file__).resolve().parent / 'TEST_codex_reuse_lifecycle2006_a'
result = json.loads((root / 'TEST_RESULT.json').read_text())
g1 = json.loads((root / 'G1_candidate/a7_g1_candidate.json').read_text())
records = []
for kind in ('G1', 'G2', 'G3'):
    doc = json.loads((root / (kind + '_candidate') / 'a7_g1_candidate.json').read_text())
    assert doc['producer_identity'] == result['producer']
    expected = ({r['question_id'] for r in doc['question_bindings']} if kind == 'G1'
                else {q for r in doc['batch_rows'] for q in r['question_ids']})
    seen = collections.Counter()
    files = sorted((root / (kind + '_run') / 'raw').glob('*.raw.json'))
    for path in files:
        body = json.loads(path.read_text())
        assert len({r['question_id'] for r in body}) == len(body)
        seen.update(r['question_id'] for r in body)
        if kind == 'G1':
            assert all(r['produced_idxs'] == [] for r in body)
        elif kind == 'G2':
            assert all(r['verdicts'] and all(v is True for v in r['verdicts'].values()) for r in body)
        else:
            assert all(r['bucket'] is None for r in body)
    assert seen == collections.Counter({q: 2 for q in expected})
    fin = json.loads((root / (kind + '_run') / 'finalization.seg01.json').read_text())
    assert fin['ledger'] == dict(scheduled=len(files), valid=len(files), invalid=0, retry=0, uncalled=0)
    assert len(files) == len(doc['batch_rows']) * 2
    records.append(dict(kind=kind,questions=len(expected),test_calls=len(files),
                        every_question_reviewed_twice=True))

trace = g1['materialization']['trace']
assert len(trace) == 382 and len({r['packet_id'] for r in trace}) == 191
assert all(r['status'] == 'answered' and r['readable'] is True for r in trace)
expected_gold = g1['materialization']['accepted_gold']
assert expected_gold == 206 and g1['materialization']['events'] == 36
scores = []
for leg, actual in result['scores'].items():
    matched = sum(len(pairs) for key,pairs in result['g2_pairs'].items() if key.split('|',1)[0] == leg)
    extras = [(key.split('|',1)[1],index) for key,indices in result['g3_idxs'].items()
              if key.split('|',1)[0] == leg for index in indices]
    assert len(set(extras)) == len(extras)
    assert actual['matched'] == matched
    assert actual['gold_n'] == expected_gold
    assert Decimal(str(actual['recall'])) == round(Decimal(matched) / expected_gold, 4)
    assert actual['state_acc'] == actual['other_meaning_acc'] == 1
    assert actual['verdicts_missing'] == 0
    assert actual['required_grading_unfinished'] is True
    assert actual['extras'] == dict(duplicate=0,key_miss=0,unsupported=0)
    assert collections.Counter((r['sid'],r['produced_idx']) for r in actual['ambiguous_rows']) == collections.Counter(extras)
    assert all(r['reason'] == 'extras_verdict_missing' for r in actual['ambiguous_rows'])
    assert actual['confirmed_wrong_accepted'] == 0
    assert actual['duplicate_violations'] == actual['open_identity_findings'] == 0
    assert actual['reliability_failed'] is False and actual['reliability_unobserved'] is False
    observed = [r for r in trace if r['arm'] == leg]
    reliability = actual['reliability']
    if observed:
        assert reliability['applicable'] is True
        assert reliability['total'] == len(observed) == 191
        assert reliability['invalid'] == reliability['rate'] == 0
        assert reliability['upper95'] == 3 / len(observed)
    else:
        assert leg == 'UNION' and reliability['applicable'] is False
        assert reliability['rate'] is None
    scores.append(dict(leg=leg,matched=matched,gold=expected_gold,
                       unresolved_extras=len(extras),original_responses=len(observed)))

# WorkOrder: every required meaning judgment is necessary. The TEST G3
# answers deliberately abstain, so even a structurally complete run cannot
# be declared a finished measurement or PASS.
assert result['decisions'] == dict(P1=None,P2=None)
print(json.dumps(dict(kind='TEST accounting and conservative decision independently recomputed',
                     model_calls=0,stages=records,scores=scores,
                     decision='INCONCLUSIVE because TEST G3 judgments are null',
                     limits='Not a real model score. Other unchanged scoring rules retain their qualified regression proof; this audit checks the newly connected population, raw judgment coverage, response accounting and final gate.'),indent=1))
