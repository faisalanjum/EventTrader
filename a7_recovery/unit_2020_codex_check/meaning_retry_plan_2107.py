"""G2 post-finalization retry filter; original publisher still owns admission."""
if __name__ == '__main__':
    import hashlib
    import os
    import runpy
    from pathlib import Path
    if os.environ.get('A7_GRADING_COMMAND') != 'preflight':
        raise ValueError('retry filter only permits the read-only preflight bootstrap')
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != os.environ['A7_RETRY_PLAN_SHA256']:
        raise ValueError('unapproved retry-filter code')
    ctx = runpy.run_path(str(Path(__file__).with_name('run_grading_2086.py')))

import a4_review_composite as R
import a7_g1_build as G
import a7_meaning_format_2105 as F


def plan(candidate, run, segment, root_sha, receipt_sha, code_sha, rule_sha):
    """Keep only still-unusable members of the original finalizer's retry set.

    This reads and records evidence, not meaning or launch permission. A null,
    false or disagreement is a usable judgment, never a reason to reroll.
    The original publisher separately refuses pending/consumed/wrong attempts.
    """
    if G.segment_state(run, segment) != 'finalized':
        raise ValueError('retry filtering requires an original finalized segment')
    root = G.load_root(run, root_sha)
    doc, _ = G.load_frozen(candidate, root['candidate_sha256'])
    if G.task_kind(doc) != 'G2':
        raise ValueError('meaning-format retry filtering is G2 only')
    whole, problems = G.whole_answers(run, segment)
    if problems:
        raise ValueError('retry filter whole replies refused: %s' % problems)

    # Re-run the original finalizer, replacing only its final write with an
    # exact comparison. It owns native admission, accounting and retry rules.
    # A missing whole record was refused above, so it cannot create one here.
    def verify_saved(path, text):
        if path != G.finalization_path(run, segment) or G._sha(text) != G._sha_file(path):
            raise ValueError('retry filter original finalization does not reproduce')

    with R._using(G, _write_new=verify_saved):
        final, _rulings, problems = G.finalize_segment(candidate, run, segment, root_sha, receipt_sha)
    if problems:
        raise ValueError('retry filter original finalization refused: %s' % problems)
    receipt = G.load_receipt(run, segment)
    rows = {r['lane_id']: r for r in receipt['rows']}
    validity = dict(final['validity'])
    binding, _parser = G.binding_and_parser('G2')
    readings, unusable, recovered = [], [], []
    with F.scope(code_sha, rule_sha):
        for lane, row in rows.items():
            if lane in final['uncalled']:
                continue
            answer, bad, audit = F.read((whole or {}).get(lane), binding(doc, row['batch_id']))
            if audit['original_valid'] != validity[lane]:
                raise ValueError('retry filter original validity drifted for %s' % lane)
            if bad:
                unusable.append(lane)
            if audit['recovered']:
                recovered.append(lane)
            readings.append({'lane_id': lane, 'answer': answer, 'problems': bad, 'audit': audit})
    return {'segment': segment, 'root_sha256': root_sha, 'receipt_sha256': receipt_sha,
            'finalization_sha256': G._sha_file(G.finalization_path(run, segment)),
            'format_code_sha256': code_sha, 'format_rule_sha256': rule_sha,
            'original_retry_lanes': final['retry'],
            'retry_lanes': [lane for lane in final['retry'] if lane in unusable],
            'unusable': unusable, 'recovered': recovered, 'readings': readings,
            'new_model_calls': 0}


if __name__ == '__main__':
    result = plan(ctx['cand'], ctx['run_dir'], int(os.environ['A7_GRADING_SEGMENT']),
                  ctx['launch']['root_sha256'], os.environ['A7_GRADING_RECEIPT_SHA256'],
                  os.environ['A7_FORMAT_CODE_SHA256'], os.environ['A7_FORMAT_RULE_SHA256'])
    print(G._plain(result), flush=True)
