"""Read-only explanation of the G1 candidate pool; never assigns a new match."""
import json
from pathlib import Path

import trace_corrected_score_2167 as T
from driver.core.fact_match import match_facts


def run():
    T.verify()
    native = json.loads(T.REPORT.read_text())
    evidence = T.U / 'CORE_RECALL_TRACE_2168.json'
    pin = '40f5ac16bdeb270e244eff1160c443f0b5bcdcf8001a6bdb4e9a3c4be96b58f0'
    assert T.G._sha_file(str(evidence)) == pin, (str(evidence), T.G._sha_file(str(evidence)), pin)
    misses = json.loads(evidence.read_text())
    T.B.bind_grading_scorer(str(T.SCORER), T.PINS[str(T.SCORER)])
    S = T.B._scorer()
    groups = {}
    for leg, case in native['cases'].items():
        for sid, answer in case['answers'].items():
            facts = T.restore_numeric_slots(answer['facts'])
            rejected = S.conflicting_driver_names({'facts': facts})
            excluded = S.facts_bearing({'facts': facts}, rejected)
            _eligible, eligible_positions = S.eligible_produced(facts)
            all_v2, positions = S._to_v2_with_positions(facts)
            gold_v2, gold_positions = S._to_v2_with_positions(
                T.restore_numeric_slots(native['key'][sid]))
            # Diagnostic only: existing exact matcher over ALL emitted facts.
            # It does not admit an excluded fact or replace a saved G1 ruling.
            exact = match_facts(gold_v2, all_v2)
            groups[(leg, sid)] = dict(
                excluded_positions=sorted(excluded),
                eligible_positions=sorted(eligible_positions.values()),
                exact_all_emitted_pairs=[(gold_positions[id(g)], positions[id(p)])
                                         for g, p in exact.links])
    rows = []
    for miss in misses:
        if 'agreed_no_candidate' not in miss['reasons']:
            continue
        group = groups[(miss['leg'], miss['sid'])]
        rows.append(dict(leg=miss['leg'], source_id=miss['sid'], gold_idx=miss['gold_idx'],
                         question_id=miss['question_id'], offered=miss['candidates'],
                         excluded_positions=group['excluded_positions'],
                         exact_all_emitted_pairs=[p for p in group['exact_all_emitted_pairs']
                                                  if p[0] == miss['gold_idx']]))
    assert len(rows) == 115
    T.verify()
    return dict(scope='All 115 agreed-no-candidate findings: candidate eligibility, not semantic truth or new credit',
                native_score_sha256=T.PINS[str(T.REPORT)],
                g1_trace_sha256=pin, code_sha256=T.G._sha_file(__file__), rows=rows)


if __name__ == '__main__':
    print(T.G._pretty(run()))
