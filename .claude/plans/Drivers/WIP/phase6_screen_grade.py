#!/usr/bin/env python3
"""THE mechanical grader (screen run time; zero AI). Exact-array evidence law."""
def grade_one(rid, resp, A):
    a=A[rid]
    if resp.get('request_id')!=a['expected_request_id']: return 'WRONG:request'
    if resp.get('anchor_id')!=a['expected_anchor_id']: return 'WRONG:anchor'
    if resp.get('abstain'):
        if any(resp.get(k) is not None for k in
               ('block_id','occurrence_id','copied_label','copied_period_evidence')):
            return 'WRONG:abstain-with-evidence'
        return 'abstain'
    if resp.get('block_id')!=a['expected_block_id']: return 'WRONG:block'
    if resp.get('occurrence_id')!=a['expected_occurrence']: return 'WRONG:occurrence'
    if resp.get('copied_label')!=a['expected_copied_label']: return 'WRONG:label'
    if resp.get('copied_period_evidence')!=a['expected_period_evidence_array']:
        return 'WRONG:period_evidence'
    return 'CORRECT'


REQUIRED_KEYS={'request_id','anchor_id','block_id','occurrence_id',
               'copied_label','copied_period_evidence','abstain'}

def grade_batch(responses, expected_rids, A):
    """STRICT whole-response grading: every expected request answered EXACTLY once;
    no extra, no duplicate, no malformed rows escape."""
    out={'per_request':{}, 'batch_errors':[]}
    if not isinstance(responses, list):
        out['batch_errors'].append('MALFORMED:not-a-list'); return out
    seen=set()
    for resp in responses:
        if not isinstance(resp, dict) or set(resp) != REQUIRED_KEYS:
            out['batch_errors'].append('MALFORMED:row'); continue
        if not (isinstance(resp['abstain'], bool)
                and all(resp[k] is None or isinstance(resp[k], str)
                        for k in ('request_id','anchor_id','block_id',
                                  'occurrence_id','copied_label'))
                and (resp['copied_period_evidence'] is None
                     or isinstance(resp['copied_period_evidence'], list))):
            out['batch_errors'].append('MALFORMED:field-type'); continue
        rid=resp['request_id']
        if rid not in expected_rids:
            out['batch_errors'].append(f'EXTRA:{rid}'); continue
        if rid in seen:
            out['batch_errors'].append(f'DUPLICATE:{rid}'); continue
        seen.add(rid)
        out['per_request'][rid]=grade_one(rid, resp, A)
    for rid in expected_rids - seen:
        out['batch_errors'].append(f'MISSING:{rid}')
    out['clean'] = (not out['batch_errors']
                    and all(v in ('CORRECT', 'abstain')
                            for v in out['per_request'].values()))
    return out
