"""Both prior rounds, four identity kinds, through real TEST native proof.

Read-only. The immutable TEST state's prompt, script, transcript and native
proof remain unchanged. An earlier round's spent-identity reader receives the
current identity in one slot; the actual proof must refuse its reuse. This
exercises the same boundary for message/request identities, which are not
stored in arbitrary fields of the workflow state.
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

A7 = Path(__file__).resolve().parents[1]
for rel in ('unit_2009/owner', 'unit_2023_source_correction',
            'unit_2041_decision_connection', 'unit_2061_settlement_connection',
            'unit_2065_closeout_connection', 'unit_2069_targeted_source',
            'unit_2076_latest_source_decisions'):
    sys.path.insert(0, str(A7 / rel))
import a4_review_composite as R
import a4_source_correction as C
import a4_source_decision as D
import a4_source_settlement as S
import a4_source_closeout as V
import a4_v6_successor_chain as X

F, K, SK = R.F, R.K, R.SK
build = Path(os.environ['A7_THIRD_TEST_BUILD'])
saved = K._load(str(build / 'TEST_RESULT.json'))
base = K._load(str(Path(saved['base']) / 'TEST_RESULT.json'))
inputs = [saved[k] for k in ('findings', 'decision_findings',
                            'settlement_findings', 'closeout_findings')]
run1, run2, current = base['first_run'], base['run2'], saved['run3']
find1, find2, findings = base['first_findings'], base['round2_findings'], saved['round3_findings']
receipt = K._load(os.path.join(current, K.RECEIPT_NAME))
field_names = ('run', 'agent', 'response', 'request')
owner_sha = R.INV.sha_file(X.__file__)
assert owner_sha == 'beed43091c4a5088f248122c3cf627ef82fd72cdbad7d9390863d1cb4ad558a7'
results = []


@F._operation
def main():
    with R.final_scope(saved['review'], saved['review_package'], bind_role=True):
        b = SK.bound(saved['key_run'], saved['key_package'])
        closed = V.bind(S.bind(D.bind(C.bind(b, saved['corrections']), saved['decision']),
                              saved['settlement']), saved['closeout'])
        bound = X.bind(closed, current)
        with X.successor_scope(bound, findings, run2, find2, inputs, ((run1, find1),)):
            original = F._spent_identities
            current_ids = original(current)
            assert all(current_ids) and receipt['allowed'] and receipt['states']

            def positive():
                got, bad = F.run_evidence(current, bound, receipt)
                assert not bad and set(got) == set(receipt['allowed']), (got, bad)
                assert all(row[0] == 'proved' for row in got.values()), got

            for earlier in (run1, run2):
                prior_ids = original(earlier)
                assert all(prior_ids), (earlier, [len(values) for values in prior_ids])
                for index, field in enumerate(field_names):
                    positive()

                    def colliding_prior(run):
                        ids = tuple(set(values) for values in original(run))
                        if os.path.abspath(run) == os.path.abspath(earlier):
                            ids[index].update(current_ids[index])
                        return ids

                    with patch.object(F, '_spent_identities', colliding_prior):
                        got, bad = F.run_evidence(current, bound, receipt)
                    refused = (set(got) == set(receipt['allowed']) and bool(bad)
                               and all(row[0] == 'unproved' for row in got.values())
                               and any(field + ' id' in p and 'already spent' in p for p in bad))
                    row = {'prior_round': earlier, 'field': field, 'positive': 'proved',
                           'saved_prior_id_count': len(prior_ids[index]),
                           'refused': refused, 'problems': bad}
                    results.append(row)
                    print(json.dumps(row), flush=True)
                    assert refused, row
                    positive()
    assert R.INV.sha_file(X.__file__) == owner_sha
    print(json.dumps({'build': str(build), 'owner_sha256': owner_sha,
                      'collision_kinds': len(results), 'positive_controls': 16,
                      'model_calls': 0, 'native_writes': 0}), flush=True)


main()
